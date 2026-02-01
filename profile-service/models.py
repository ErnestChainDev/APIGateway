from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from shared.database import Base

class UserProfile(Base):
    __tablename__ = "user_profile"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_profile_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    full_name: Mapped[str] = mapped_column(String(255), default="")
    year_level: Mapped[str] = mapped_column(String(50), default="")

    interests: Mapped[str] = mapped_column(Text, default="")
    career_goals: Mapped[str] = mapped_column(Text, default="")
    preferred_program: Mapped[str] = mapped_column(String(20), default="")  # CS/IT/IS/BTVTED or ""
    skills: Mapped[str] = mapped_column(Text, default="")

    notes: Mapped[str] = mapped_column(Text, default="")
