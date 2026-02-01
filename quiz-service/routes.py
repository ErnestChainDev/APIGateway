import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from shared.database import db_dependency
from .schemas import (
    QuestionCreateIn, OptionCreateIn,
    QuestionOut, OptionOut,
    AttemptStartOut, SubmitQuizIn, SubmitQuizOut
)
from .crud import (
    create_question, add_option,
    list_questions, get_options_for_question,
    start_attempt, submit_attempt, category_breakdown
)

router = APIRouter()
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-recommendation-engine:8005")

def build_router(SessionLocal):
    get_db = db_dependency(SessionLocal)

    def current_user_id(request: Request) -> int:
        user = getattr(request.state, "user", None)
        return int(user["sub"]) if user and "sub" in user else 0

    # Admin-ish endpoints (you can protect later)
    @router.post("/questions", response_model=QuestionOut)
    def create_q(payload: QuestionCreateIn, db: Session = Depends(get_db)):
        q = create_question(db, payload.category, payload.text)
        return q

    @router.post("/questions/{question_id}/options", response_model=OptionOut)
    def create_opt(question_id: int, payload: OptionCreateIn, db: Session = Depends(get_db)):
        opt = add_option(db, question_id, payload.text, payload.is_correct)
        return OptionOut(id=opt.id, question_id=opt.question_id, text=opt.text)

    @router.get("/questions", response_model=list[QuestionOut])
    def get_qs(db: Session = Depends(get_db)):
        return list_questions(db)

    @router.get("/questions/{question_id}/options", response_model=list[OptionOut])
    def get_opts(question_id: int, db: Session = Depends(get_db)):
        opts = get_options_for_question(db, question_id)
        return [OptionOut(id=o.id, question_id=o.question_id, text=o.text) for o in opts]

    @router.post("/attempts/start", response_model=AttemptStartOut)
    def start(request: Request, db: Session = Depends(get_db)):
        uid = current_user_id(request)
        a = start_attempt(db, uid)
        return AttemptStartOut(attempt_id=a.id)

    @router.post("/attempts/{attempt_id}/submit", response_model=SubmitQuizOut)
    async def submit(attempt_id: int, payload: SubmitQuizIn, request: Request, db: Session = Depends(get_db)):
        uid = current_user_id(request)

        # ensure attempt belongs to user
        # (simple check)
        # if you want stricter, query attempt first and validate.
        try:
            attempt = submit_attempt(db, attempt_id, [a.model_dump() for a in payload.answers])
        except ValueError:
            raise HTTPException(404, "Attempt not found")

        breakdown = category_breakdown(db, attempt_id)

        # call AI service for recommendation
        rec_payload = {
            "user_id": uid,
            "attempt_id": attempt.id,
            "score": attempt.score,
            "total": attempt.total,
            **breakdown,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(f"{AI_SERVICE_URL}/ai/recommend", json=rec_payload)
            recommendation = r.json() if r.status_code == 200 else {"detail": "AI recommend failed"}
        except Exception:
            recommendation = {"detail": "AI service unavailable"}

        return SubmitQuizOut(
            attempt_id=attempt.id,
            score=attempt.score,
            total=attempt.total,
            recommendation=recommendation,
        )

    return router
