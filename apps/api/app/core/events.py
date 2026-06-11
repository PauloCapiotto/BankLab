import json
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

STREAM = "banklab.transactions"


async def publish_event(event: dict) -> None:
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.xadd(STREAM, {"data": json.dumps(event)})
        finally:
            await client.aclose()
    except Exception:
        logger.exception(
            "Falha ao publicar evento no Redis: %s", event.get("event_type")
        )
