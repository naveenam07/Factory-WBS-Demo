from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AdvisorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    advisor_id: str
    name: str


class AdvisorsResponse(BaseModel):
    advisors: list[AdvisorOut]
    trace_id: str | None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    advisor_id: str
    client_name: str
    account_type: str | None
    last4: str
    cash_balance: float


class AdvisorAccountsResponse(BaseModel):
    advisor_id: str
    advisor_name: str
    accounts: list[AccountOut]
    trace_id: str | None


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    quantity: int
    cost_basis: float
    price: float | None
    market_value: float | None


class PositionsResponse(BaseModel):
    account_id: str
    advisor_id: str
    positions: list[PositionOut]
    total_market_value: float
    trace_id: str | None


class OrderRequest(BaseModel):
    advisor_id: str
    account_id: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)


class OrderResponse(BaseModel):
    confirmation_number: str
    status: str
    account_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    estimated_value: float
    trace_id: str | None


class TransferRequest(BaseModel):
    advisor_id: str
    from_account_id: str
    to_account_id: str
    amount: float = Field(gt=0, allow_inf_nan=False)


class TransferResponse(BaseModel):
    confirmation_number: str
    status: str
    amount: float
    from_account_id: str
    to_account_id: str
    from_cash_balance: float
    to_cash_balance: float
    trace_id: str | None


class HealthResponse(BaseModel):
    status: str
    service: str
    trace_id: str | None
