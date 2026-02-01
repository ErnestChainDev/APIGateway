from sqlalchemy.orm import Session
from .models import Course

def list_courses(db: Session, program: str | None = None):
    q = db.query(Course)
    if program:
        q = q.filter(Course.program == program)
    return q.order_by(Course.id.desc()).all()

def get_course(db: Session, course_id: int):
    return db.query(Course).filter(Course.id == course_id).first()

def create_course(db: Session, payload: dict):
    c = Course(**payload)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def delete_course(db: Session, course_id: int) -> bool:
    c = get_course(db, course_id)
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True
