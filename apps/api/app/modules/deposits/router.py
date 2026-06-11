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
from app.modules.deposits.schemas import DepositRequest, DepositResponse

router = APIRouter(tags=["deposits"])


async def _find_existing(
    session: AsyncSession, user: models.User | uuid.UUID, key: str
) -> DepositResponse | None:
    user_id: uuid.UUID = user if isinstance(user, uuid.UUID) else user.id
    result = await session.execute(
        select(models.Transaction, models.Account)
        .join(models.Account, models.Transaction.account_id == models.Account.id)
        .where(
            models.Transaction.idempotency_key == key,
            models.Transaction.type == "deposit",
            models.Account.user_id == user_id,
        )
    )
    row = result.first()
    if row is None:
        return None
    tx, account = row
    return DepositResponse(
        transaction_id=str(tx.id),
        status=tx.status,
        new_balance=f"{account.balance:.2f}",
    )


@router.post("/deposits", response_model=DepositResponse, status_code=201)
async def create_deposit(
    payload: DepositRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DepositResponse:
    if not idempotency_key:
        raise APIError(
            400, "IDEMPOTENCY_KEY_REQUIRED", "O header Idempotency-Key é obrigatório."
        )

    existing = await _find_existing(session, user, idempotency_key)
    if existing is not None:
        return existing

    user_id: uuid.UUID = user.id

    result = await session.execute(
        select(models.Account)
        .where(
            models.Account.id == payload.account_id,
            models.Account.user_id == user_id,
        )
        .with_for_update()
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "Conta não encontrada.")
    if account.status != "active":
        raise APIError(422, "ACCOUNT_NOT_ACTIVE", "A conta não está ativa.")

    now = dt.datetime.now(dt.timezone.utc)
    tx = models.Transaction(
        account_id=account.id,
        type="deposit",
        status="completed",
        amount=payload.amount,
        description=payload.description,
        idempotency_key=idempotency_key,
        completed_at=now,
    )
    session.add(tx)
    account.balance = account.balance + payload.amount
    try:
        await session.flush()
        await record_audit(
            session,
            actor_user_id=user_id,
            action="deposit.completed",
            entity_type="transaction",
            entity_id=tx.id,
            metadata={"amount": f"{payload.amount:.2f}", "account_id": str(account.id)},
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
            "event_type": "transaction.deposit.completed",
            "transaction_id": str(tx.id),
            "account_id": str(account.id),
            "user_id": str(user_id),
            "amount": f"{payload.amount:.2f}",
            "occurred_at": now.isoformat(),
        }
    )

    return DepositResponse(
        transaction_id=str(tx.id),
        status=tx.status,
        new_balance=f"{account.balance:.2f}",
    )
