from sqlalchemy.orm import Session
from .models import UserProfile


def get_profile(db: Session, user_id: int) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def create_profile(db: Session, user_id: int, payload: dict) -> UserProfile:
    p = UserProfile(user_id=user_id, **payload)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_me(db: Session, user_id: int, payload: dict) -> UserProfile:
    """
    Update ONLY the current user's profile.
    Fields not provided remain unchanged.
    """
    p = get_profile(db, user_id)

    if not p:
        # If profile doesn't exist yet, create it
        return create_profile(db, user_id, payload)

    for field, value in payload.items():
        if hasattr(p, field):
            setattr(p, field, value)

    db.commit()
    db.refresh(p)
    return p


def upsert_profile(db: Session, user_id: int, payload: dict) -> UserProfile:
    """
    Backward-compatible upsert (used by GET /me bootstrap).
    """
    p = get_profile(db, user_id)

    if not p:
        p = UserProfile(user_id=user_id, **payload)
        db.add(p)
    else:
        for field, value in payload.items():
            if hasattr(p, field):
                setattr(p, field, value)

    db.commit()
    db.refresh(p)
    return p
