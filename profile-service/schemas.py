from pydantic import BaseModel, Field

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
