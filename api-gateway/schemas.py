from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


# Authentication Schemas
MAX_BCRYPT_BYTES = 72

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def bcrypt_max_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_BCRYPT_BYTES:
            raise ValueError("Password too long (max 72 bytes for bcrypt).")
        return v

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def bcrypt_max_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_BCRYPT_BYTES:
            raise ValueError("Password too long (max 72 bytes for bcrypt).")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class VerifyIn(BaseModel):
    token: str

class VerifyOut(BaseModel):
    sub: str
    email: str

# Profile Schemas
class ProfileUpsertIn(BaseModel):
    full_name: str = Field(default="")
    year_level: str = Field(default="")

    # CBF inputs
    interests: str = Field(default="", description="Comma-separated interests, e.g. 'programming, networking'")
    career_goals: str = Field(default="", description="Career goal text, e.g. 'software developer, data analyst'")
    preferred_program: str = Field(
        default="",
        description="Optional target program: ComSci/IT/IS/BTVTED",
        pattern=r"^(|ComSci|IT|IS|BTVTED)$",
    )
    skills: str = Field(
        default="",
        description="Comma-separated skills/keywords, e.g. 'python, sql, ui/ux'",
    )

    # Existing
    notes: str = Field(default="")

class ProfileOut(BaseModel):
    user_id: int
    full_name: str
    year_level: str

    # CBF outputs / stored profile text
    interests: str
    career_goals: str
    preferred_program: str
    skills: str

    notes: str

# Course Schemas
class CourseIn(BaseModel):
    code: str
    title: str
    description: str = ""
    program: str = Field(pattern="^(CS|IT|IS|BTVTED)$")
    level: str = ""
    tags: str = ""

class CourseOut(CourseIn):
    id: int

# Quiz Schemas
class QuestionCreateIn(BaseModel):
    category: str = Field(default="general")
    text: str

class OptionCreateIn(BaseModel):
    text: str
    is_correct: bool = False

class QuestionOut(BaseModel):
    id: int
    category: str
    text: str

class OptionOut(BaseModel):
    id: int
    question_id: int
    text: str

class AttemptStartOut(BaseModel):
    attempt_id: int

class SubmitAnswerIn(BaseModel):
    question_id: int
    selected_option_id: int

class SubmitQuizIn(BaseModel):
    answers: list[SubmitAnswerIn]

class SubmitQuizOut(BaseModel):
    attempt_id: int
    score: int
    total: int
    recommendation: dict

# Chat Schemas
class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)

class ChatOut(BaseModel):
    reply: str


# Recommendation Schemas
class RecommendIn(BaseModel):
    user_id: int
    attempt_id: int
    score: int = Field(ge=0)
    total: int = Field(gt=0)

    # optional: category breakdown (future-proof)
    logic: int = 0
    programming: int = 0
    networking: int = 0
    design: int = 0

class RecommendOut(BaseModel):
    program: str
    confidence: int
    rationale: str


# Feedback Schemas
class FeedbackIn(BaseModel):
    type: str = Field(pattern="^(recommendation|chat|course)$")
    reference_id: int = 0
    rating: int = Field(ge=1, le=5)
    comment: str = ""

class FeedbackOut(BaseModel):
    id: int
    user_id: int
    type: str
    reference_id: int
    rating: int
    comment: str