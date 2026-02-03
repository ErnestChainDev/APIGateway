# api-gateway/main.py
import os
import httpx
from fastapi import FastAPI, Request, HTTPException, status, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

from .schemas import (
    RegisterIn, LoginIn, VerifyIn,
    ProfileUpsertIn, CourseIn,
    QuestionCreateIn, OptionCreateIn, SubmitQuizIn,
    RecommendIn, ChatIn, FeedbackIn
)

load_dotenv()

app = FastAPI(title="API Gateway", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs
SERVICES = {
    "auth": os.environ["AUTH_SERVICE_URL"],
    "profile": os.environ["PROFILE_SERVICE_URL"],
    "course": os.environ["COURSE_SERVICE_URL"],
    "quiz": os.environ["QUIZ_SERVICE_URL"],
    "ai": os.environ["AI_SERVICE_URL"],
    "chat": os.environ["CHAT_SERVICE_URL"],
    "feedback": os.environ["FEEDBACK_SERVICE_URL"],
}

# Public routes (no authentication required)
PUBLIC_ROUTES = [
    "/auth/register",
    "/auth/login",
    "/auth/verify",
    "/health",
    "/",
]


# Middleware for authentication
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    
    # Skip auth for public routes
    if any(path.startswith(route) for route in PUBLIC_ROUTES):
        return await call_next(request)
    
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid authorization header"}
        )
    
    token = auth_header.split(" ")[1]
    
    # Verify token with auth service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            verify_response = await client.post(
                f"{SERVICES['auth']}/auth/verify",
                json={"token": token}
            )
        
        if verify_response.status_code != 200:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"}
            )
        
        user_data = verify_response.json()
        request.state.user = user_data
        
    except httpx.RequestError as e:
        logger.error(f"Auth service error: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Authentication service unavailable"}
        )
    
    return await call_next(request)


# Proxy function
async def proxy_request(
    service_name: str,
    path: str,
    method: str,
    request: Request,
    body_dict: dict | None = None,
    timeout: float = 30.0
):
    """Forward request to the appropriate microservice"""
    
    service_url = SERVICES.get(service_name)
    if not service_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found"
        )
    
    # Build target URL
    target_url = f"{service_url}{path}"
    
    # Copy headers (exclude host)
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # Add user info to headers if authenticated
    if hasattr(request.state, "user") and request.state.user:
        headers["X-User-ID"] = str(request.state.user.get("sub", ""))
        headers["X-User-Email"] = str(request.state.user.get("email", ""))
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                params=request.query_params,
                json=body_dict if body_dict else None,
            )
        
        return JSONResponse(
            status_code=response.status_code,
            content=response.json() if response.text else None,
        )
    
    except httpx.TimeoutException:
        logger.error(f"Timeout calling {service_name}: {target_url}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Service '{service_name}' timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"Error calling {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service '{service_name}' unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal gateway error"
        )


# Health check
@app.get("/health", operation_id="health_check", tags=["Health"])
async def health_check():
    """Check if the API Gateway is healthy"""
    return {"status": "healthy", "service": "api-gateway"}


# Auth routes
@app.post("/auth/register", operation_id="auth_register", tags=["Authentication"])
async def auth_register(payload: RegisterIn, request: Request):
    """Register a new user"""
    return await proxy_request("auth", "/auth/register", "POST", request, payload.model_dump())

@app.post("/auth/login", operation_id="auth_login", tags=["Authentication"])
async def auth_login(payload: LoginIn, request: Request):
    """Login and get access token"""
    return await proxy_request("auth", "/auth/login", "POST", request, payload.model_dump())

@app.post("/auth/verify", operation_id="auth_verify", tags=["Authentication"])
async def auth_verify(payload: VerifyIn, request: Request):
    """Verify a JWT token"""
    return await proxy_request("auth", "/auth/verify", "POST", request, payload.model_dump())


# Profile routes
@app.get("/profile/me", operation_id="profile_get_me", tags=["Profile"])
async def profile_get_me(request: Request):
    """Get current user's profile"""
    return await proxy_request("profile", "/profile/me", "GET", request)

@app.put("/profile/me", operation_id="profile_update_me", tags=["Profile"])
async def profile_update_me(payload: ProfileUpsertIn, request: Request):
    """Update current user's profile"""
    return await proxy_request("profile", "/profile/me", "PUT", request, payload.model_dump())

@app.get("/profile/by-user/{user_id}", operation_id="profile_get_by_user", tags=["Profile"])
async def profile_get_by_user(user_id: int, request: Request):
    """Get profile by user ID"""
    return await proxy_request("profile", f"/profile/by-user/{user_id}", "GET", request)


# Course routes
@app.get("/courses/", operation_id="courses_list", tags=["Courses"])
async def courses_list(request: Request, program: str | None = None):
    """List all courses, optionally filtered by program"""
    return await proxy_request("course", "/courses/", "GET", request)

@app.get("/courses/{course_id}", operation_id="courses_get_one", tags=["Courses"])
async def courses_get_one(course_id: int, request: Request):
    """Get a specific course by ID"""
    return await proxy_request("course", f"/courses/{course_id}", "GET", request)

@app.post("/courses/", operation_id="courses_create", tags=["Courses"])
async def courses_create(payload: CourseIn, request: Request):
    """Create a new course"""
    return await proxy_request("course", "/courses/", "POST", request, payload.model_dump())

@app.delete("/courses/{course_id}", operation_id="courses_delete", tags=["Courses"])
async def courses_delete(course_id: int, request: Request):
    """Delete a course"""
    return await proxy_request("course", f"/courses/{course_id}", "DELETE", request)


# Quiz routes
@app.post("/quiz/questions", operation_id="quiz_create_question", tags=["Quiz"])
async def quiz_create_question(payload: QuestionCreateIn, request: Request):
    """Create a new quiz question"""
    return await proxy_request("quiz", "/quiz/questions", "POST", request, payload.model_dump())

@app.post("/quiz/questions/{question_id}/options", operation_id="quiz_create_option", tags=["Quiz"])
async def quiz_create_option(question_id: int, payload: OptionCreateIn, request: Request):
    """Add an option to a question"""
    return await proxy_request("quiz", f"/quiz/questions/{question_id}/options", "POST", request, payload.model_dump())

@app.get("/quiz/questions", operation_id="quiz_list_questions", tags=["Quiz"])
async def quiz_list_questions(request: Request):
    """List all quiz questions"""
    return await proxy_request("quiz", "/quiz/questions", "GET", request)

@app.get("/quiz/questions/{question_id}/options", operation_id="quiz_get_options", tags=["Quiz"])
async def quiz_get_options(question_id: int, request: Request):
    """Get options for a specific question"""
    return await proxy_request("quiz", f"/quiz/questions/{question_id}/options", "GET", request)

@app.post("/quiz/attempts/start", operation_id="quiz_start_attempt", tags=["Quiz"])
async def quiz_start_attempt(request: Request):
    """Start a new quiz attempt"""
    return await proxy_request("quiz", "/quiz/attempts/start", "POST", request)

@app.post("/quiz/attempts/{attempt_id}/submit", operation_id="quiz_submit_attempt", tags=["Quiz"])
async def quiz_submit_attempt(attempt_id: int, payload: SubmitQuizIn, request: Request):
    """Submit quiz answers"""
    return await proxy_request("quiz", f"/quiz/attempts/{attempt_id}/submit", "POST", request, payload.model_dump(), timeout=60.0)


# AI routes
@app.post("/ai/recommend", operation_id="ai_recommend", tags=["AI Recommendations"])
async def ai_recommend(payload: RecommendIn, request: Request):
    """Get AI-powered course recommendations"""
    return await proxy_request("ai", "/ai/recommend", "POST", request, payload.model_dump(), timeout=60.0)


# Chat routes
@app.post("/chat/", operation_id="chat_send_message", tags=["Chat"])
async def chat_send_message(payload: ChatIn, request: Request):
    """Send a chat message"""
    return await proxy_request("chat", "/chat/", "POST", request, payload.model_dump(), timeout=60.0)

@app.get("/chat/recent", operation_id="chat_get_recent", tags=["Chat"])
async def chat_get_recent(request: Request):
    """Get recent chat messages"""
    return await proxy_request("chat", "/chat/recent", "GET", request)


# Feedback routes
@app.post("/feedback/", operation_id="feedback_submit", tags=["Feedback"])
async def feedback_submit(payload: FeedbackIn, request: Request):
    """Submit user feedback"""
    return await proxy_request("feedback", "/feedback/", "POST", request, payload.model_dump())

@app.get("/feedback/stats", operation_id="feedback_get_stats", tags=["Feedback"])
async def feedback_get_stats(request: Request):
    """Get feedback statistics"""
    return await proxy_request("feedback", "/feedback/stats", "GET", request)


# Root endpoint
@app.get("/", operation_id="root", tags=["Root"])
async def root():
    """API Gateway information"""
    return {
        "service": "API Gateway",
        "version": "1.0.0",
        "available_services": list(SERVICES.keys()),
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
