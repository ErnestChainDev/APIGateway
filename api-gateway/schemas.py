from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


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


# Forgot Password Schemas
class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def bcrypt_max_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_BCRYPT_BYTES:
            raise ValueError("Password too long (max 72 bytes for bcrypt).")
        return v


class GenericMsgOut(BaseModel):
    detail: str


# Profile Schemas
class ProfileUpsertIn(BaseModel):
    full_name: str = Field(default="")
    strand: str = Field(default="")

    interests: str = Field(default="", description="Comma-separated interests, e.g. 'programming, networking'")
    career_goals: str = Field(default="", description="Career goal text, e.g. 'software developer, data analyst'")
    preferred_program: str = Field(
        default="",
        description="Optional target program: BSCS/BSIT/BSIS/BTVTED",
        pattern=r"^(|BSCS|BSIT|BSIS|BTVTED)$",
    )
    skills: str = Field(
        default="",
        description="Comma-separated skills/keywords, e.g. 'python, sql, ui/ux'",
    )
    notes: str = Field(default="")


class ProfileOut(BaseModel):
    user_id: int
    full_name: str
    strand: str
    interests: str
    career_goals: str
    preferred_program: str
    skills: str
    notes: str


# Course Schemas
class LessonItem(BaseModel):
    title: str
    content: str


class CourseIn(BaseModel):
    code: str
    title: str
    description: str = ""
    program: str = Field(pattern="^(BSCS|BSIT|BSIS|BTVTED)$")
    level: str = ""
    tags: str = ""
    lessons: list[LessonItem] = Field(default_factory=list)


class CourseProgressIn(BaseModel):
    course_id: int
    lesson_index: int = 0
    lesson_title: str = ""
    status: str = Field(default="in_progress", pattern="^(in_progress|completed)$")


class CourseOut(CourseIn):
    id: int


# Quiz Schemas
QuizCategory = Literal["bscs", "bsit", "bsis", "btvted"]
QuestionType = Literal["mcq", "fill_blank_choice", "drag_drop"]
AttemptStatus = Literal["in_progress", "completed", "cancelled"]
AnswerState = Literal["answered", "missed", "unanswered"]


class QuestionCreateIn(BaseModel):
    category: QuizCategory
    text: str
    question_type: QuestionType = "mcq"
    points: int = Field(default=1, ge=1)
    time_limit_seconds: int = Field(default=40, ge=5, le=300)
    image_url: Optional[str] = None
    blank_placeholder: Optional[str] = None


class OptionCreateIn(BaseModel):
    text: str
    is_correct: bool = False
    display_order: int = 0


class QuestionOut(BaseModel):
    id: int
    category: str
    text: str
    question_type: QuestionType
    points: int
    time_limit_seconds: int
    image_url: Optional[str] = None
    blank_placeholder: Optional[str] = None


class OptionOut(BaseModel):
    id: int
    question_id: int
    text: str
    display_order: int


class AttemptStartOut(BaseModel):
    attempt_id: int
    status: AttemptStatus


class SubmitAnswerIn(BaseModel):
    question_id: int
    selected_option_id: int


class DragDropMappingIn(BaseModel):
    item_key: str
    target_key: str


class SaveAnswerIn(BaseModel):
    question_id: int
    answer_state: AnswerState = "answered"
    selected_option_id: Optional[int] = None
    mappings: list[DragDropMappingIn] = Field(default_factory=list)


class SubmitQuizIn(BaseModel):
    answers: list[SaveAnswerIn]


class SubmitQuizOut(BaseModel):
    attempt_id: int
    status: AttemptStatus
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