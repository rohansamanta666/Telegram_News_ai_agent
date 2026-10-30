"""Normalized article data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Article(BaseModel):
    """Normalized schema for news articles across all providers."""
    title: str = Field(..., description="Headline of the article")
    source: str = Field(..., description="Canonical name of the source (e.g. 'the_guardian', 'hacker_news')")
    url: str = Field(..., description="Direct web link to the original article")
    published_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="ISO 8601 published timestamp or best estimate"
    )
    summary: str = Field(..., description="Short summary, snippet, or lead text")
    author: Optional[str] = Field(None, description="Author or editorial team name if known")

    def to_dict(self) -> dict:
        return self.model_dump()

