from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI
from openai import RateLimitError
from openai.types.chat import ChatCompletionMessageParam
import os, time, random
from typing import cast

from shared.database import db_dependency
from .schemas import ChatIn, ChatOut
from .crud import save_message, recent_messages
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

def get_or_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set")

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            # Optional but recommended for attribution/analytics on OpenRouter:
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "course-reco-chat-service"),
        },
    )

def call_with_backoff(fn, max_retries: int = 5):
    base = 0.5
    for attempt in range(max_retries):
        try:
            return fn()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            time.sleep(min(15.0, base * (2 ** attempt)) + random.uniform(0, 0.25))

def build_router(SessionLocal):
    get_db = db_dependency(SessionLocal)

    def current_user_id(request: Request) -> int:
        user = getattr(request.state, "user", None)
        return int(user["sub"]) if user and "sub" in user else 0

    def build_messages(db: Session, uid: int, user_text: str, limit: int = 12, extra_system: str | None = None):
        history = list(reversed(recent_messages(db, uid, limit=limit)))

        system_prompt = (
            "You are a helpful AI chat assistant. "
            "Be concise, correct, and ask at most one clarifying question when needed."
        )

        if extra_system:
            system_prompt += " " + extra_system

        msgs = [{"role": "system", "content": system_prompt}]

        for m in history:
            if m.role in ("user", "assistant") and m.content:
                msgs.append({"role": m.role, "content": m.content})

        msgs.append({"role": "user", "content": user_text})
        return cast(list[ChatCompletionMessageParam], msgs)


    def call_llm(db: Session, uid: int, user_text: str) -> str:
        client = get_or_client()
        model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1-0528:free")

        input_messages = build_messages(db, uid, user_text, limit=10)

        try:
            resp = call_with_backoff(lambda: client.chat.completions.create(
                model=model,
                messages=input_messages,
            ))
            if resp is not None and hasattr(resp, "choices") and resp.choices:
                reply = (resp.choices[0].message.content or "").strip()
            else:
                reply = ""
            return reply or "Sorry—I'm having trouble generating a response right now."
        except RateLimitError:
            raise HTTPException(status_code=429, detail="Rate limited. Please retry in a few seconds.")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM provider error: {type(e).__name__}")

    @router.post("/", response_model=ChatOut)
    def chat(payload: ChatIn, request: Request, db: Session = Depends(get_db)):
        uid = current_user_id(request)

        save_message(db, uid, "user", payload.message)
        reply = call_llm(db, uid, payload.message)
        save_message(db, uid, "assistant", reply)

        return ChatOut(reply=reply)

    @router.get("/recent", response_model=list[dict])
    def recent(request: Request, db: Session = Depends(get_db)):
        uid = current_user_id(request)
        msgs = recent_messages(db, uid, limit=20)
        return [{"role": m.role, "content": m.content} for m in reversed(msgs)]

    return router
