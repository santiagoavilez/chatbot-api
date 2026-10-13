import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4096)]

Role = Literal["user", "system", "assistant", "tool"]

# Only free models allowed
AllowedOpenRouterModels = Literal[
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "thinkingmachines/inkling:free",
]


class ChatRequest(BaseModel):
    content: Content
    model: AllowedOpenRouterModels


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    content: str
    conversation_id: uuid.UUID
    role: Role
    model: str | None
    created_at: datetime
