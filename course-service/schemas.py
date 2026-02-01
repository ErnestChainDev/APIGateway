from pydantic import BaseModel, Field

class CourseIn(BaseModel):
    code: str
    title: str
    description: str = ""
    program: str = Field(pattern="^(CS|IT|IS|BTVTED)$")
    level: str = ""
    tags: str = ""

class CourseOut(CourseIn):
    id: int
