import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class TransferRequest(BaseModel):
    source_account_id: uuid.UUID
    destination_account_number: str
    amount: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)


class TransferResponse(BaseModel):
    transfer_id: str
    status: str
    source_transaction_id: str
    destination_transaction_id: str
    new_balance: str
