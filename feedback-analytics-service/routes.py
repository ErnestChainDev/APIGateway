from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from shared.database import db_dependency
from .schemas import FeedbackIn, FeedbackOut
from .crud import create_feedback, stats

router = APIRouter()

def build_router(SessionLocal):
    get_db = db_dependency(SessionLocal)

    def current_user_id(request: Request) -> int:
        user = getattr(request.state, "user", None)
        return int(user["sub"]) if user and "sub" in user else 0

    @router.post("/", response_model=FeedbackOut)
    def submit(payload: FeedbackIn, request: Request, db: Session = Depends(get_db)):
        uid = current_user_id(request)
        f = create_feedback(db, uid, payload.model_dump())
        return FeedbackOut(
            id=f.id, user_id=f.user_id, type=f.type, reference_id=f.reference_id, rating=f.rating, comment=f.comment
        )

    @router.get("/stats", response_model=list[dict])
    def get_stats(db: Session = Depends(get_db)):
        return stats(db)

    return router
