import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.modules.auth.deps import get_current_user
from app.modules.transactions.schemas import TransactionOut, to_transaction_out

router = APIRouter(tags=["summary"])


class SummaryResponse(BaseModel):
    total_balance: str
    monthly_inflow: str
    monthly_outflow: str
    unread_notifications: int
    latest_transactions: list[TransactionOut]


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    now = dt.datetime.now(dt.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_balance = (
        await session.execute(
            select(func.coalesce(func.sum(models.Account.balance), 0)).where(
                models.Account.user_id == user.id
            )
        )
    ).scalar_one()

    async def month_sum(types: list[str]) -> Decimal:
        return (
            await session.execute(
                select(func.coalesce(func.sum(models.Transaction.amount), 0))
                .join(
                    models.Account,
                    models.Transaction.account_id == models.Account.id,
                )
                .where(
                    models.Account.user_id == user.id,
                    models.Transaction.type.in_(types),
                    models.Transaction.status == "completed",
                    models.Transaction.created_at >= month_start,
                )
            )
        ).scalar_one()

    inflow = await month_sum(["deposit", "transfer_in"])
    outflow = await month_sum(["transfer_out"])

    unread = (
        await session.execute(
            select(func.count())
            .select_from(models.Notification)
            .where(
                models.Notification.user_id == user.id,
                models.Notification.read_at.is_(None),
            )
        )
    ).scalar_one()

    latest = (
        (
            await session.execute(
                select(models.Transaction)
                .join(
                    models.Account,
                    models.Transaction.account_id == models.Account.id,
                )
                .where(models.Account.user_id == user.id)
                .order_by(models.Transaction.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    return SummaryResponse(
        total_balance=f"{Decimal(total_balance):.2f}",
        monthly_inflow=f"{Decimal(inflow):.2f}",
        monthly_outflow=f"{Decimal(outflow):.2f}",
        unread_notifications=unread,
        latest_transactions=[to_transaction_out(tx) for tx in latest],
    )
