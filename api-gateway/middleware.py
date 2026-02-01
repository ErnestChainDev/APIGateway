import os
import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")

# Public paths that don't require auth
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
}

# Public prefixes (auth endpoints)
PUBLIC_PREFIXES = (
    "/auth/register",
    "/auth/login",
    "/auth/verify",
)

def _is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)

async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if _is_public_path(path):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Missing Bearer token"})

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Missing token"})

    # Verify token via auth-service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{AUTH_SERVICE_URL}/auth/verify", json={"token": token})

        if r.status_code != 200:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        user = r.json()  # expected: {"sub": "...", "email": "..."}
        request.state.user = user

    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "Auth service unavailable"})
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "Gateway auth error"})

    return await call_next(request)
