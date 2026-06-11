from pydantic import BaseModel

from app import models


class TransactionOut(BaseModel):
    id: str
    account_id: str
    related_account_id: str | None
    type: str
    status: str
    amount: str
    description: str | None
    created_at: str
    completed_at: str | None


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    page: int
    page_size: int
    total: int


def to_transaction_out(tx: models.Transaction) -> TransactionOut:
    return TransactionOut(
        id=str(tx.id),
        account_id=str(tx.account_id),
        related_account_id=(
            str(tx.related_account_id) if tx.related_account_id else None
        ),
        type=tx.type,
        status=tx.status,
        amount=f"{tx.amount:.2f}",
        description=tx.description,
        created_at=tx.created_at.isoformat(),
        completed_at=tx.completed_at.isoformat() if tx.completed_at else None,
    )
