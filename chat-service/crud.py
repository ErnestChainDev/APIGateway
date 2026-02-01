from sqlalchemy.orm import Session
from .models import ChatMessage

def save_message(db: Session, user_id: int, role: str, content: str):
    m = ChatMessage(user_id=user_id, role=role, content=content)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m

def recent_messages(db: Session, user_id: int, limit: int = 10):
    q = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)

    # Prefer created_at if your model has it; else fallback to id
    if hasattr(ChatMessage, "created_at"):
        q = q.order_by(ChatMessage.created_at.desc())  # type: ignore
    else:
        q = q.order_by(ChatMessage.id.desc())

    return q.limit(limit).all()
