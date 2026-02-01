import os
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

router = APIRouter()

SERVICE_MAP = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001"),
    "profile": os.getenv("PROFILE_SERVICE_URL", "http://profile-service:8002"),
    "courses": os.getenv("COURSE_SERVICE_URL", "http://course-service:8003"),
    "quiz": os.getenv("QUIZ_SERVICE_URL", "http://quiz-service:8004"),
    "ai": os.getenv("AI_SERVICE_URL", "http://ai-recommendation-engine:8005"),
    "chat": os.getenv("CHAT_SERVICE_URL", "http://chat-service:8006"),
    "feedback": os.getenv("FEEDBACK_SERVICE_URL", "http://feedback-analytics-service:8007"),
}

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}

def _clean_headers(headers: dict) -> dict:
    out = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        out[k] = v
    return out

def _inject_user_headers(request: Request, headers: dict) -> dict:
    """
    Optional: pass user info downstream (so services can read it without re-verifying JWT).
    Your downstream services can read:
    - x-user-id
    - x-user-email
    """
    user = getattr(request.state, "user", None)
    if user:
        if "sub" in user:
            headers["x-user-id"] = str(user["sub"])
        if "email" in user:
            headers["x-user-email"] = str(user["email"])
    return headers

async def _proxy(request: Request, base_url: str, upstream_path: str) -> Response:
    url = f"{base_url}{upstream_path}"
    method = request.method

    # Forward query params + body
    params = dict(request.query_params)
    body = await request.body()

    headers = _clean_headers(dict(request.headers))
    headers = _inject_user_headers(request, headers)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.request(
                method=method,
                url=url,
                params=params,
                content=body,
                headers=headers,
            )

        # Forward response as-is
        resp_headers = _clean_headers(dict(r.headers))
        return Response(
            content=r.content,
            status_code=r.status_code,
            headers=resp_headers,
            media_type=r.headers.get("content-type", "application/json"),
        )

    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Upstream service unavailable")

# ---- Route bindings ----
@router.api_route("/auth/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_auth(request: Request, path: str):
    return await _proxy(request, SERVICE_MAP["auth"], f"/auth/{path}")

@router.api_route("/profile/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_profile(request: Request, path: str):
    return await _proxy(request, SERVICE_MAP["profile"], f"/profile/{path}")

@router.api_route("/courses/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_courses(request: Request, path: str):
    return await _proxy(request, SERVICE_MAP["courses"], f"/courses/{path}")

@router.api_route("/quiz/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_quiz(request: Request, path: str):
    return await _proxy(request, SERVICE_MAP["quiz"], f"/quiz/{path}")

@router.api_route("/ai/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_ai(request: Request, path: str):
    return await _proxy(request, SERVICE_MAP["ai"], f"/ai/{path}")

@router.api_route("/chat/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_chat(request: Request, path: str):
    return await _proxy(request, SERVICE_MAP["chat"], f"/chat/{path}")

@router.api_route("/feedback/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_feedback(request: Request, path: str):
    return await _proxy(request, SERVICE_MAP["feedback"], f"/feedback/{path}")
