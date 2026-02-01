from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from shared.database import Base

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    type: Mapped[str] = mapped_column(String(50))     # "recommendation" | "chat" | "course"
    reference_id: Mapped[int] = mapped_column(Integer, default=0)  # attempt_id or message_id etc.
    rating: Mapped[int] = mapped_column(Integer, default=0)        # 1-5
    comment: Mapped[str] = mapped_column(Text, default="")
