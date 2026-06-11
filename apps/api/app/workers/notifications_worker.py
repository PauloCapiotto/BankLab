import asyncio
import json
import logging
import uuid
from decimal import Decimal

import redis.asyncio as aioredis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.events import STREAM

logger = logging.getLogger(__name__)

GROUP = "notifications"
CONSUMER = "worker-1"


def format_brl(amount: str) -> str:
    value = f"{Decimal(amount):,.2f}"
    return "R$ " + value.replace(",", "X").replace(".", ",").replace("X", ".")


def build_notifications(event: dict) -> list[dict]:
    event_type = event.get("event_type")
    if event_type == "transaction.deposit.completed":
        return [
            {
                "user_id": event["user_id"],
                "type": "transaction",
                "title": "Depósito recebido",
                "message": (
                    f"Você recebeu um depósito de {format_brl(event['amount'])}."
                ),
                "dedup_key": (
                    f"{event_type}:{event['transaction_id']}:{event['user_id']}"
                ),
            }
        ]
    if event_type == "transaction.transfer.completed":
        return [
            {
                "user_id": event["source_user_id"],
                "type": "transaction",
                "title": "Transferência enviada",
                "message": f"Você enviou {format_brl(event['amount'])}.",
                "dedup_key": (
                    f"{event_type}:{event['source_transaction_id']}"
                    f":{event['source_user_id']}"
                ),
            },
            {
                "user_id": event["destination_user_id"],
                "type": "transaction",
                "title": "Transferência recebida",
                "message": f"Você recebeu {format_brl(event['amount'])}.",
                "dedup_key": (
                    f"{event_type}:{event['destination_transaction_id']}"
                    f":{event['destination_user_id']}"
                ),
            },
        ]
    logger.warning("Evento desconhecido ignorado: %s", event_type)
    return []


async def handle_event(session: AsyncSession, event: dict) -> None:
    for item in build_notifications(event):
        stmt = (
            insert(models.Notification)
            .values(
                user_id=uuid.UUID(item["user_id"]),
                type=item["type"],
                title=item["title"],
                message=item["message"],
                dedup_key=item["dedup_key"],
            )
            .on_conflict_do_nothing(index_elements=["dedup_key"])
        )
        await session.execute(stmt)
    await session.commit()


async def ensure_group(client: aioredis.Redis) -> None:
    try:
        await client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def process_entries(client: aioredis.Redis, batches: list) -> None:
    for _stream, entries in batches or []:
        for entry_id, fields in entries:
            try:
                event = json.loads(fields["data"])
                async with SessionLocal() as session:
                    await handle_event(session, event)
                await client.xack(STREAM, GROUP, entry_id)
            except Exception:
                logger.exception("Falha ao processar evento %s", entry_id)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    await ensure_group(client)
    logger.info("Worker de notificações iniciado.")

    # Reprocessa mensagens pendentes (entregues e não confirmadas) ao subir.
    pending = await client.xreadgroup(GROUP, CONSUMER, {STREAM: "0"}, count=100)
    await process_entries(client, pending)

    while True:
        messages = await client.xreadgroup(
            GROUP, CONSUMER, {STREAM: ">"}, count=10, block=5000
        )
        await process_entries(client, messages)


if __name__ == "__main__":
    asyncio.run(run())
