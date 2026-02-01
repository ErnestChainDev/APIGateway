from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from shared.database import Base

class Course(Base):
    __tablename__ = "course"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    program: Mapped[str] = mapped_column(String(20), index=True)  # CS/IT/IS/BTVTED
    level: Mapped[str] = mapped_column(String(50), default="")    # e.g. 1st year
    tags: Mapped[str] = mapped_column(Text, default="")           # comma-separated
