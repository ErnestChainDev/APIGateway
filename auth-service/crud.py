from sqlalchemy.orm import Session
from .models import UserAuth

def get_user_by_email(db: Session, email: str):
    return db.query(UserAuth).filter(UserAuth.email == email).first()

def create_user(db: Session, email: str, password_hash: str):
    u = UserAuth(email=email, password_hash=password_hash)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
