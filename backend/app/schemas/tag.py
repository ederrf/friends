"""Schemas de tag / interesse."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    """Payload para adicionar uma tag a um amigo."""

    tag: str = Field(..., min_length=1, max_length=80)


class TagRead(BaseModel):
    """Tag persistida."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    friend_id: int
    tag: str
    created_at: datetime


class InterestSummary(BaseModel):
    """Agregacao de uma tag com contagem de amigos."""

    tag: str
    friend_count: int
