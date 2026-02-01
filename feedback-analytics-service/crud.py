from sqlalchemy import text
from sqlalchemy.orm import Session
from .models import Feedback

def create_feedback(db: Session, user_id: int, payload: dict):
    f = Feedback(user_id=user_id, **payload)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f

def stats(db: Session):
    # very simple stats
    rows = db.execute(text("""
        SELECT type, COUNT(*) AS cnt, AVG(rating) AS avg_rating
        FROM feedback
        GROUP BY type
    """)).fetchall()
    return [{"type": r[0], "count": int(r[1]), "avg_rating": float(r[2] or 0)} for r in rows]
