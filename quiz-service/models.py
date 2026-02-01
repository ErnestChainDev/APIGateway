from sqlalchemy import Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from shared.database import Base

class Question(Base):
    __tablename__ = "question"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(50), default="general")  # programming/networking/logic/design
    text: Mapped[str] = mapped_column(Text)

class AnswerOption(Base):
    __tablename__ = "answer_option"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

class QuizAttempt(Base):
    __tablename__ = "quiz_attempt"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)

class AttemptAnswer(Base):
    __tablename__ = "attempt_answer"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_attempt.id"), index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"), index=True)
    selected_option_id: Mapped[int] = mapped_column(Integer, ForeignKey("answer_option.id"))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
