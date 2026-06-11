import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.core.events import publish_event
from app.modules.audit.service import record_audit
from app.modules.auth.deps import get_current_user
from app.modules.transfers.schemas import TransferRequest, TransferResponse

router = APIRouter(tags=["transfers"])


async def _find_existing(
    session: AsyncSession, user_id: uuid.UUID, key: str
) -> TransferResponse | None:
    result = await session.execute(
        select(models.Transaction, models.Account)
        .join(models.Account, models.Transaction.account_id == models.Account.id)
        .where(
            models.Transaction.idempotency_key == key,
            models.Transaction.type == "transfer_out",
            models.Account.user_id == user_id,
        )
    )
    row = result.first()
    if row is None:
        return None
    tx_out, source_account = row
    tx_in = (
        await session.execute(
            select(models.Transaction).where(
                models.Transaction.idempotency_key == key,
                models.Transaction.type == "transfer_in",
            )
        )
    ).scalar_one()
    return TransferResponse(
        transfer_id=str(tx_out.id),
        status=tx_out.status,
        source_transaction_id=str(tx_out.id),
        destination_transaction_id=str(tx_in.id),
        new_balance=f"{source_account.balance:.2f}",
    )


@router.post("/transfers", response_model=TransferResponse, status_code=201)
async def create_transfer(
    payload: TransferRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TransferResponse:
    if not idempotency_key:
        raise APIError(
            400, "IDEMPOTENCY_KEY_REQUIRED", "O header Idempotency-Key é obrigatório."
        )

    # Capturado antes de qualquer rollback: após rollback o objeto ORM expira
    # e acessar user.id dispararia lazy-load fora do greenlet (MissingGreenlet).
    user_id = user.id

    existing = await _find_existing(session, user_id, idempotency_key)
    if existing is not None:
        return existing

    source_check = (
        await session.execute(
            select(models.Account).where(
                models.Account.id == payload.source_account_id,
                models.Account.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if source_check is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "Conta não encontrada.")

    destination_check = (
        await session.execute(
            select(models.Account).where(
                models.Account.number == payload.destination_account_number
            )
        )
    ).scalar_one_or_none()
    if destination_check is None:
        raise APIError(
            404, "DESTINATION_ACCOUNT_NOT_FOUND", "Conta de destino não encontrada."
        )
    if destination_check.id == source_check.id:
        raise APIError(
            422, "SAME_ACCOUNT", "A conta de destino deve ser diferente da origem."
        )

    locked = (
        await session.execute(
            select(models.Account)
            .where(models.Account.id.in_([source_check.id, destination_check.id]))
            .order_by(models.Account.id)
            .with_for_update()
        )
    ).scalars().all()
    by_id = {account.id: account for account in locked}
    source = by_id[source_check.id]
    destination = by_id[destination_check.id]

    if source.status != "active":
        raise APIError(422, "ACCOUNT_NOT_ACTIVE", "A conta de origem não está ativa.")
    if destination.status != "active":
        raise APIError(
            422, "ACCOUNT_NOT_ACTIVE", "A conta de destino não está ativa."
        )
    if source.balance < payload.amount:
        raise APIError(
            422,
            "INSUFFICIENT_BALANCE",
            "Saldo insuficiente para concluir a transferência.",
        )

    now = dt.datetime.now(dt.timezone.utc)
    tx_out = models.Transaction(
        account_id=source.id,
        related_account_id=destination.id,
        type="transfer_out",
        status="completed",
        amount=payload.amount,
        description=payload.description,
        idempotency_key=idempotency_key,
        completed_at=now,
    )
    tx_in = models.Transaction(
        account_id=destination.id,
        related_account_id=source.id,
        type="transfer_in",
        status="completed",
        amount=payload.amount,
        description=payload.description,
        idempotency_key=idempotency_key,
        completed_at=now,
    )
    session.add_all([tx_out, tx_in])
    source.balance = source.balance - payload.amount
    destination.balance = destination.balance + payload.amount

    # flush + audit + commit dentro do try: o IntegrityError da constraint
    # única dispara já no flush, e o fallback precisa alcançá-lo.
    try:
        await session.flush()
        await record_audit(
            session,
            actor_user_id=user_id,
            action="transfer.completed",
            entity_type="transaction",
            entity_id=tx_out.id,
            metadata={
                "amount": f"{payload.amount:.2f}",
                "source_account_id": str(source.id),
                "destination_account_id": str(destination.id),
            },
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await _find_existing(session, user_id, idempotency_key)
        if existing is not None:
            return existing
        raise

    await publish_event(
        {
            "event_type": "transaction.transfer.completed",
            "source_transaction_id": str(tx_out.id),
            "destination_transaction_id": str(tx_in.id),
            "source_account_id": str(source.id),
            "destination_account_id": str(destination.id),
            "source_user_id": str(user_id),
            "destination_user_id": str(destination.user_id),
            "amount": f"{payload.amount:.2f}",
            "occurred_at": now.isoformat(),
        }
    )

    return TransferResponse(
        transfer_id=str(tx_out.id),
        status=tx_out.status,
        source_transaction_id=str(tx_out.id),
        destination_transaction_id=str(tx_in.id),
        new_balance=f"{source.balance:.2f}",
    )
