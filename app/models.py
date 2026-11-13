from pydantic import BaseModel


class Advisor(BaseModel):
    advisor_id: str
    name: str


class Account(BaseModel):
    account_id: str
    advisor_id: str
    client_name: str
    account_type: str | None
    last4: str
    account_number: str
    client_ssn: str
    cash_balance: float


class Position(BaseModel):
    account_id: str
    symbol: str
    quantity: int
    cost_basis: float
