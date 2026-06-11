import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    account_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)


class DepositResponse(BaseModel):
    transaction_id: str
    status: str
    new_balance: str
