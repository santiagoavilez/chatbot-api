import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ConversationCreate(BaseModel):
    title: Title | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationUpdate(BaseModel):
    title: Title
