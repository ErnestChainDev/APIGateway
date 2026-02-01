from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from shared.database import db_dependency
from .schemas import CourseIn, CourseOut
from .crud import list_courses, get_course, create_course, delete_course

router = APIRouter()

def build_router(SessionLocal):
    get_db = db_dependency(SessionLocal)

    @router.get("/", response_model=list[CourseOut])
    def get_all(program: str | None = Query(default=None), db: Session = Depends(get_db)):
        return list_courses(db, program)

    @router.get("/{course_id}", response_model=CourseOut)
    def get_one(course_id: int, db: Session = Depends(get_db)):
        c = get_course(db, course_id)
        if not c:
            raise HTTPException(404, "Course not found")
        return c

    @router.post("/", response_model=CourseOut)
    def create(payload: CourseIn, db: Session = Depends(get_db)):
        return create_course(db, payload.model_dump())

    @router.delete("/{course_id}", response_model=dict)
    def remove(course_id: int, db: Session = Depends(get_db)):
        ok = delete_course(db, course_id)
        if not ok:
            raise HTTPException(404, "Course not found")
        return {"deleted": True}

    return router
