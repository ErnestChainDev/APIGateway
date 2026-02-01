import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shared.database import db_dependency
from shared.utils import hash_password, verify_password, create_access_token, decode_token

from .schemas import RegisterIn, LoginIn, TokenOut, VerifyIn, VerifyOut
from .crud import get_user_by_email, create_user

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "change-this")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def get_db_dep(SessionLocal):
    return db_dependency(SessionLocal)

def build_router(SessionLocal):
    get_db = get_db_dep(SessionLocal)

    @router.post("/register", response_model=dict)
    def register(payload: RegisterIn, db: Session = Depends(get_db)):
        existing = get_user_by_email(db, payload.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        u = create_user(db, payload.email, hash_password(payload.password))
        return {"id": u.id, "email": u.email}

    @router.post("/login", response_model=TokenOut)
    def login(payload: LoginIn, db: Session = Depends(get_db)):
        u = get_user_by_email(db, payload.email)
        if not u or not verify_password(payload.password, u.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token(
            {"sub": str(u.id), "email": u.email},
            secret=JWT_SECRET,
            algorithm=JWT_ALGORITHM,
            expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        )
        return TokenOut(access_token=token)

    @router.post("/verify", response_model=VerifyOut)
    def verify(payload: VerifyIn):
        try:
            data = decode_token(payload.token, JWT_SECRET, JWT_ALGORITHM)
            return VerifyOut(sub=str(data.get("sub")), email=str(data.get("email")))
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    return router
