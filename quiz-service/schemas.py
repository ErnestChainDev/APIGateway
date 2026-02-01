from pydantic import BaseModel, Field

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
