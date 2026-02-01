from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from shared.database import db_dependency
from .schemas import ProfileUpsertIn, ProfileOut
from .crud import get_profile, upsert_profile, update_me

router = APIRouter()

def build_router(SessionLocal):
    get_db = db_dependency(SessionLocal)

    def current_user_id(request: Request) -> int:
        # set by api-gateway middleware (/auth/verify)
        user = getattr(request.state, "user", None)
        return int(user["sub"]) if user and "sub" in user else 0

    @router.get("/me", response_model=ProfileOut)
    def me(request: Request, db: Session = Depends(get_db)):
        uid = current_user_id(request)
        p = get_profile(db, uid)
        if not p:
            p = upsert_profile(db, uid, {
                "full_name": "",
                "year_level": "",
                "interests": "",
                "career_goals": "",
                "preferred_program": "",
                "skills": "",
                "notes": "",
            })
        return ProfileOut(
            user_id=uid,
            full_name=p.full_name,
            year_level=p.year_level,
            interests=p.interests,
            career_goals=p.career_goals,
            preferred_program=p.preferred_program,
            skills=p.skills,
            notes=p.notes,
        )
    
    @router.get("/by-user/{user_id}", response_model=ProfileOut)
    def by_user(user_id: int, db: Session = Depends(get_db)):
        p = get_profile(db, user_id)
        if not p:
            p = upsert_profile(db, user_id, {
                "full_name": "",
                "year_level": "",
                "interests": "",
                "career_goals": "",
                "preferred_program": "",
                "skills": "",
                "notes": "",
            })
        return ProfileOut(
            user_id=user_id,
            full_name=p.full_name,
            year_level=p.year_level,
            interests=p.interests,
            career_goals=p.career_goals,
            preferred_program=p.preferred_program,
            skills=p.skills,
            notes=p.notes,
        )


    @router.put("/me", response_model=ProfileOut)
    def update_me(payload: ProfileUpsertIn, request: Request, db: Session = Depends(get_db)):
        uid = current_user_id(request)
        p = upsert_profile(db, uid, payload.model_dump())
        return ProfileOut(
            user_id=uid,
            full_name=p.full_name,
            year_level=p.year_level,
            interests=p.interests,
            career_goals=p.career_goals,
            preferred_program=p.preferred_program,
            skills=p.skills,
            notes=p.notes,
        )

    return router
