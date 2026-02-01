from pydantic import BaseModel, Field

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
