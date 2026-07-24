from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class ContactSubmissionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=2, max_length=100)]
    email: EmailStr
    company: Annotated[str, Field(max_length=150)] = ""
    project_type: Annotated[str, Field(max_length=100)] = ""
    budget: Annotated[str, Field(max_length=50)] = ""
    message: Annotated[str, Field(min_length=10, max_length=5000)]
    website: Annotated[str, Field(max_length=200)] = ""

    @model_validator(mode="before")
    @classmethod
    def accept_frontend_field_names(cls, value: Any) -> Any:
        if isinstance(value, dict) and "projectType" in value:
            normalized = dict(value)
            normalized.setdefault("project_type", normalized.pop("projectType"))
            return normalized
        return value

    @field_validator("name", "company", "project_type", "budget", "message")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split()) if "\n" not in value else value.strip()


class ContactSubmissionResponse(BaseModel):
    id: int
    status: str
    message: str
