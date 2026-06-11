import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.modules.auth.deps import get_current_user
from app.modules.transactions.schemas import (
    TransactionListResponse,
    to_transaction_out,
)

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    account_id: uuid.UUID | None = Query(default=None),
    from_: dt.date | None = Query(default=None, alias="from"),
    to: dt.date | None = Query(default=None),
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TransactionListResponse:
    filters = [models.Account.user_id == user.id]
    if account_id is not None:
        filters.append(models.Transaction.account_id == account_id)
    if from_ is not None:
        filters.append(
            models.Transaction.created_at
            >= dt.datetime.combine(from_, dt.time.min, tzinfo=dt.timezone.utc)
        )
    if to is not None:
        filters.append(
            models.Transaction.created_at
            < dt.datetime.combine(
                to + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc
            )
        )
    if type is not None:
        filters.append(models.Transaction.type == type)
    if status is not None:
        filters.append(models.Transaction.status == status)
    if search:
        filters.append(models.Transaction.description.ilike(f"%{search}%"))

    base = (
        select(models.Transaction)
        .join(models.Account, models.Transaction.account_id == models.Account.id)
        .where(*filters)
    )

    total = (
        await session.execute(
            select(func.count()).select_from(base.subquery())
        )
    ).scalar_one()

    items = (
        (
            await session.execute(
                base.order_by(models.Transaction.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return TransactionListResponse(
        items=[to_transaction_out(tx) for tx in items],
        page=page,
        page_size=page_size,
        total=total,
    )
