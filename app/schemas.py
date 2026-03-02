from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator
import re


class ShortenRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        # Basic URL format check
        pattern = re.compile(
            r"^https?://"
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
            r"localhost|"
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r"(?::\d+)?"
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        if not pattern.match(v):
            raise ValueError("Invalid URL format")
        return v


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class StatsResponse(BaseModel):
    original_url: str
    short_code: str
    click_count: int
    created_at: datetime
