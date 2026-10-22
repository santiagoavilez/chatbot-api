import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import UUID, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MessageMetric(Base):
    """Generation metrics of an assistant message (1:1 with ``messages``)."""

    __tablename__ = "message_metrics"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    generation_id: Mapped[str] = mapped_column(String(100))
    finish_reason: Mapped[str] = mapped_column(String(30))
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 8))
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"MessageMetric(message_id={self.message_id!r}, "
            f"generation_id={self.generation_id!r}, finish_reason={self.finish_reason!r})"
        )
