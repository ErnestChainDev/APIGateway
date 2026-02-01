from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from .middleware import auth_middleware
from .routes import router

app = FastAPI(title="API Gateway", version="1.0.0")

# Global auth middleware (protects all routes except allowlist in middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)

# Reverse-proxy routes
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "healthy", "service": "api-gateway"}
