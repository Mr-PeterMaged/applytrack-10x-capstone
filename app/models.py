from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        local, separator, domain = value.partition("@")
        if (
            not separator
            or not local
            or "." not in domain
            or "@" in domain
            or any(c.isspace() for c in value)
        ):
            raise ValueError("Enter a valid email address")
        return value


class Status(str, Enum):
    saved = "saved"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


class ApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=160)
    status: Status = Status.saved
    applied_on: date = Field(default_factory=date.today)
    follow_up_on: date | None = None
    notes: str = Field(default="", max_length=3000)
