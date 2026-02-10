# api-gateway/main.py
from __future__ import annotations

import os
import logging
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response

from .schemas import (
    RegisterIn, LoginIn, VerifyIn,
    ForgotPasswordIn, ResetPasswordIn,
    ProfileUpsertIn, CourseIn,
    QuestionCreateIn, OptionCreateIn, SubmitQuizIn,
    RecommendIn, ChatIn, FeedbackIn,
)

load_dotenv()

app = FastAPI(title="API Gateway", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-gateway")


# -------------------------
# Helpers / Config
# -------------------------

def _get_env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None or val.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val.strip()


def _parse_origins(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return ["*"]
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


SERVICES = {
    "auth": _get_env("AUTH_SERVICE_URL").rstrip("/"),
    "profile": _get_env("PROFILE_SERVICE_URL").rstrip("/"),
    "course": _get_env("COURSE_SERVICE_URL").rstrip("/"),
    "quiz": _get_env("QUIZ_SERVICE_URL").rstrip("/"),
    "ai": _get_env("AI_SERVICE_URL").rstrip("/"),
    "chat": _get_env("CHAT_SERVICE_URL").rstrip("/"),
    "feedback": _get_env("FEEDBACK_SERVICE_URL").rstrip("/"),
}

# IMPORTANT: DO NOT include "/" here, it makes everything public.
PUBLIC_PREFIXES = (
    "/auth/register",
    "/auth/login",
    "/auth/verify",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/google/login",
    "/auth/google/callback",
    "/health",
)

# Root exact path should be public:
PUBLIC_EXACT = ("/",)

origins = _parse_origins(os.getenv("CORS_ORIGINS", "*"))
allow_credentials = True
if origins == ["*"]:
    # Browsers reject "*" with credentials
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


# ✅ DO NOT FORWARD hop-by-hop headers (esp. content-length)
HOP_BY_HOP_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade",
}


def _copy_headers(request: Request) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in request.headers.items():
        if k.lower() in HOP_BY_HOP_HEADERS:
            continue
        out[k] = v
    return out


def _attach_user_headers(headers: dict[str, str], request: Request) -> None:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        return

    uid = str(user.get("sub") or "").strip()
    email = str(user.get("email") or "").strip()

    if uid:
        headers["X-User-ID"] = uid
    if email:
        headers["X-User-Email"] = email


# -------------------------
# ✅ Program header support for Quiz (from Profile Service)
# -------------------------

PROGRAM_MAP = {
    "comsci": "comsci",
    "it": "it",
    "is": "is",
    "btvted": "btvted",
}


def _normalize_program(val: Any) -> str | None:
    if not val:
        return None
    # ProfileUpsertIn accepts ComSci/IT/IS/BTVTED; normalize to lowercase keys
    s = str(val).strip().lower()
    return PROGRAM_MAP.get(s)


async def _fetch_program_from_profile(request: Request) -> str | None:
    """
    Calls profile-service /profile/me and returns normalized preferred_program (or None).
    Uses the same Authorization header from the incoming request.
    """
    auth = request.headers.get("authorization")
    if not auth:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{SERVICES['profile']}/profile/me",
                headers={"Authorization": auth},
            )
    except httpx.RequestError:
        return None

    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    return _normalize_program(data.get("preferred_program"))


def _build_target_url(service_name: str, path: str) -> str:
    base = SERVICES.get(service_name)
    if not base:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    return f"{base}{path}"


def _is_json_request(request: Request) -> bool:
    ct = (request.headers.get("content-type") or "").lower()
    return "application/json" in ct


async def forward(
    *,
    service: str,
    path: str,
    method: str,
    request: Request,
    json_body: Optional[dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Response:
    target_url = _build_target_url(service, path)
    headers = _copy_headers(request)
    _attach_user_headers(headers, request)

    # ✅ Attach user's program for Quiz service using Profile service
    if service == "quiz":
        prog = await _fetch_program_from_profile(request)
        if prog:
            headers["X-Program"] = prog

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            kwargs: dict[str, Any] = {
                "method": method,
                "url": target_url,
                "headers": headers,
                "params": request.query_params,
            }

            # If route provided json_body explicitly, use it
            if json_body is not None:
                kwargs["json"] = json_body
            else:
                # Otherwise, forward raw body for POST/PUT/PATCH
                if method.upper() in ("POST", "PUT", "PATCH"):
                    body = await request.body()
                    if body:
                        # Keep original content-type and forward raw bytes
                        kwargs["content"] = body

            resp = await client.request(**kwargs)

    except httpx.TimeoutException:
        logger.error("Timeout calling %s: %s", service, target_url)
        raise HTTPException(status_code=504, detail=f"Service '{service}' timeout")
    except httpx.RequestError as e:
        logger.error("Error calling %s: %s (%s)", service, target_url, e)
        raise HTTPException(status_code=503, detail=f"Service '{service}' unavailable")

    # Redirect passthrough for OAuth flows
    if resp.status_code in (301, 302, 303, 307, 308):
        location = resp.headers.get("location")
        if not location:
            return JSONResponse(status_code=resp.status_code, content={"detail": "Redirect without location"})

        out = RedirectResponse(url=location, status_code=resp.status_code)

        # forward set-cookie headers if any
        for sc in resp.headers.get_list("set-cookie"):
            out.headers.append("set-cookie", sc)

        return out

    content_type = resp.headers.get("content-type", "") or ""
    if "application/json" in content_type.lower():
        data = resp.json() if resp.text else None
        return JSONResponse(status_code=resp.status_code, content=data)

    # For non-json, forward as text (simple)
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=content_type.split(";")[0] if content_type else None,
    )


async def _verify_token(token: str) -> dict[str, Any]:
    """
    Verify token via auth-service and normalize returned payload.
    REQUIRED: sub, email
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{SERVICES['auth']}/auth/verify",
                json={"token": token},
            )
    except httpx.RequestError as e:
        logger.error("Auth service error: %s", e)
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

    try:
        data: Any = r.json()
    except Exception:
        data = r.text

    if r.status_code != 200:
        detail = "Invalid or expired token"
        if isinstance(data, dict):
            detail = data.get("detail") or data.get("message") or detail
        elif isinstance(data, str) and data.strip():
            detail = data
        raise HTTPException(status_code=401, detail=detail)

    payload = data
    if isinstance(payload, dict) and "user" in payload and isinstance(payload["user"], dict):
        payload = payload["user"]

    if not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    sub = payload.get("sub")
    email = payload.get("email")

    if not sub:
        raise HTTPException(status_code=401, detail="Token missing sub")
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email")

    return {"sub": str(sub), "email": str(email)}


# -------------------------
# Auth Middleware
# -------------------------

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # ✅ Let CORS preflight pass through (no auth here)
    if request.method == "OPTIONS":
        return await call_next(request)

    if _is_public(request.url.path):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid authorization header"},
        )

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid authorization header"},
        )

    try:
        user = await _verify_token(token)
        request.state.user = user
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    return await call_next(request)


# -------------------------
# Health + Root
# -------------------------

@app.get("/health", operation_id="health_check", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}


@app.get("/", operation_id="root", tags=["Root"])
async def root():
    return {
        "service": "API Gateway",
        "version": "1.0.0",
        "available_services": list(SERVICES.keys()),
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# -------------------------
# Auth Routes
# -------------------------

@app.post("/auth/register", operation_id="auth_register", tags=["Authentication"])
async def auth_register(payload: RegisterIn, request: Request):
    return await forward(service="auth", path="/auth/register", method="POST", request=request, json_body=payload.model_dump())

@app.post("/auth/login", operation_id="auth_login", tags=["Authentication"])
async def auth_login(payload: LoginIn, request: Request):
    return await forward(service="auth", path="/auth/login", method="POST", request=request, json_body=payload.model_dump())

@app.post("/auth/verify", operation_id="auth_verify", tags=["Authentication"])
async def auth_verify(payload: VerifyIn, request: Request):
    return await forward(service="auth", path="/auth/verify", method="POST", request=request, json_body=payload.model_dump())

@app.post("/auth/forgot-password", operation_id="auth_forgot_password", tags=["Authentication"])
async def auth_forgot_password(payload: ForgotPasswordIn, request: Request):
    return await forward(service="auth", path="/auth/forgot-password", method="POST", request=request, json_body=payload.model_dump())

@app.post("/auth/reset-password", operation_id="auth_reset_password", tags=["Authentication"])
async def auth_reset_password(payload: ResetPasswordIn, request: Request):
    return await forward(service="auth", path="/auth/reset-password", method="POST", request=request, json_body=payload.model_dump())

@app.get("/auth/google/login", operation_id="auth_google_login", tags=["Authentication"])
async def auth_google_login(request: Request, return_to: str | None = None):
    # return_to is forwarded via query_params automatically
    return await forward(service="auth", path="/auth/google/login", method="GET", request=request)

@app.get("/auth/google/callback", operation_id="auth_google_callback", tags=["Authentication"])
async def auth_google_callback(request: Request, code: str, state: str | None = None):
    # code/state are forwarded via query_params automatically
    return await forward(service="auth", path="/auth/google/callback", method="GET", request=request)


# -------------------------
# Profile Routes
# -------------------------

@app.get("/profile/me", operation_id="profile_get_me", tags=["Profile"])
async def profile_get_me(request: Request):
    return await forward(service="profile", path="/profile/me", method="GET", request=request)

@app.put("/profile/me", operation_id="profile_update_me", tags=["Profile"])
async def profile_update_me(payload: ProfileUpsertIn, request: Request):
    return await forward(service="profile", path="/profile/me", method="PUT", request=request, json_body=payload.model_dump())


# -------------------------
# Course Routes
# -------------------------

@app.get("/courses/", operation_id="courses_list", tags=["Courses"])
async def courses_list(request: Request, program: str | None = None):
    # program will be forwarded via request.query_params if frontend passes it,
    # but if you want to enforce it from this signature:
    return await forward(service="course", path="/courses/", method="GET", request=request)

@app.get("/courses/{course_id}", operation_id="courses_get_one", tags=["Courses"])
async def courses_get_one(course_id: int, request: Request):
    return await forward(service="course", path=f"/courses/{course_id}", method="GET", request=request)

@app.post("/courses/", operation_id="courses_create", tags=["Courses"])
async def courses_create(payload: CourseIn, request: Request):
    return await forward(service="course", path="/courses/", method="POST", request=request, json_body=payload.model_dump())

@app.delete("/courses/{course_id}", operation_id="courses_delete", tags=["Courses"])
async def courses_delete(course_id: int, request: Request):
    return await forward(service="course", path=f"/courses/{course_id}", method="DELETE", request=request)


# -------------------------
# Quiz Routes
# -------------------------

@app.post("/quiz/questions", operation_id="quiz_create_question", tags=["Quiz"])
async def quiz_create_question(payload: QuestionCreateIn, request: Request):
    return await forward(service="quiz", path="/quiz/questions", method="POST", request=request, json_body=payload.model_dump())

@app.post("/quiz/questions/{question_id}/options", operation_id="quiz_create_option", tags=["Quiz"])
async def quiz_create_option(question_id: int, payload: OptionCreateIn, request: Request):
    return await forward(service="quiz", path=f"/quiz/questions/{question_id}/options", method="POST", request=request, json_body=payload.model_dump())

@app.get("/quiz/questions", operation_id="quiz_list_questions", tags=["Quiz"])
async def quiz_list_questions(request: Request):
    return await forward(service="quiz", path="/quiz/questions", method="GET", request=request)

@app.get("/quiz/questions/{question_id}/options", operation_id="quiz_get_options", tags=["Quiz"])
async def quiz_get_options(question_id: int, request: Request):
    return await forward(service="quiz", path=f"/quiz/questions/{question_id}/options", method="GET", request=request)

@app.post("/quiz/attempts/start", operation_id="quiz_start_attempt", tags=["Quiz"])
async def quiz_start_attempt(request: Request):
    return await forward(service="quiz", path="/quiz/attempts/start", method="POST", request=request)

@app.get("/quiz/attempts/{attempt_id}/questions", operation_id="quiz_attempt_questions", tags=["Quiz"])
async def quiz_attempt_questions(attempt_id: int, request: Request):
    return await forward(
        service="quiz",
        path=f"/quiz/attempts/{attempt_id}/questions",
        method="GET",
        request=request,
    )

@app.post("/quiz/attempts/{attempt_id}/submit", operation_id="quiz_submit_attempt", tags=["Quiz"])
async def quiz_submit_attempt(attempt_id: int, payload: SubmitQuizIn, request: Request):
    return await forward(
        service="quiz",
        path=f"/quiz/attempts/{attempt_id}/submit",
        method="POST",
        request=request,
        json_body=payload.model_dump(),
        timeout=60.0,
    )


# -------------------------
# AI Routes
# -------------------------

@app.post("/ai/recommend", operation_id="ai_recommend", tags=["AI Recommendations"])
async def ai_recommend(payload: RecommendIn, request: Request):
    return await forward(
        service="ai",
        path="/ai/recommend",
        method="POST",
        request=request,
        json_body=payload.model_dump(),
        timeout=60.0,
    )


# -------------------------
# Chat Routes
# -------------------------

@app.post("/chat/", operation_id="chat_send_message", tags=["Chat"])
async def chat_send_message(payload: ChatIn, request: Request):
    return await forward(
        service="chat",
        path="/chat/",
        method="POST",
        request=request,
        json_body=payload.model_dump(),
        timeout=60.0,
    )

@app.get("/chat/recent", operation_id="chat_get_recent", tags=["Chat"])
async def chat_get_recent(request: Request):
    return await forward(service="chat", path="/chat/recent", method="GET", request=request)


# -------------------------
# Feedback Routes
# -------------------------

@app.post("/feedback/", operation_id="feedback_submit", tags=["Feedback"])
async def feedback_submit(payload: FeedbackIn, request: Request):
    return await forward(service="feedback", path="/feedback/", method="POST", request=request, json_body=payload.model_dump())

@app.get("/feedback/stats", operation_id="feedback_get_stats", tags=["Feedback"])
async def feedback_get_stats(request: Request):
    return await forward(service="feedback", path="/feedback/stats", method="GET", request=request)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)