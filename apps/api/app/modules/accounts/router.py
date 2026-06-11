import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.modules.accounts.schemas import AccountOut
from app.modules.auth.deps import get_current_user

router = APIRouter(tags=["accounts"])


def to_account_out(account: models.Account) -> AccountOut:
    return AccountOut(
        id=str(account.id),
        branch=account.branch,
        number=account.number,
        type=account.type,
        balance=f"{account.balance:.2f}",
        status=account.status,
    )


@router.get("/accounts", response_model=list[AccountOut])
async def list_accounts(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AccountOut]:
    result = await session.execute(
        select(models.Account)
        .where(models.Account.user_id == user.id)
        .order_by(models.Account.created_at)
    )
    return [to_account_out(a) for a in result.scalars().all()]


@router.get("/accounts/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    result = await session.execute(
        select(models.Account).where(
            models.Account.id == account_id, models.Account.user_id == user.id
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "Conta não encontrada.")
    return to_account_out(account)
