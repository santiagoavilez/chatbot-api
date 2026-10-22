import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_metric import MessageMetric


class MessageMetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        message_id: uuid.UUID,
        generation_id: str,
        finish_reason: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: Decimal | float | None,
        latency_ms: int,
    ) -> MessageMetric:
        metric = MessageMetric(
            message_id=message_id,
            generation_id=generation_id,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=None if cost is None else Decimal(str(cost)),
            latency_ms=latency_ms,
        )
        self.session.add(metric)
        await self.session.flush()
        return metric
