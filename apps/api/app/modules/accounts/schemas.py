from pydantic import BaseModel


class AccountOut(BaseModel):
    id: str
    branch: str
    number: str
    type: str
    balance: str
    status: str
