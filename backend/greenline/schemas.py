"""API request/response models (SPEC-M1 §6.4, §7)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Cadence = Literal["weekly", "biweekly", "semimonthly", "monthly", "quarterly", "annual"]


class AccountOut(BaseModel):
    id: int
    name: str
    institution: str
    type: str
    balance_cents: int | None
    balance_as_of: date | None

    model_config = {"from_attributes": True}


class AccountPatch(BaseModel):
    name: str | None = None
    type: Literal["checking", "savings"] | None = None


class ImportBatchOut(BaseModel):
    id: int
    filename: str
    imported_at: datetime
    parser: str
    rows_total: int
    rows_added: int
    rows_duplicate: int
    date_min: date | None
    date_max: date | None

    model_config = {"from_attributes": True}


class TransactionOut(BaseModel):
    id: int
    account_id: int
    posted_date: date
    amount_cents: int
    description: str
    payee_key: str
    category_raw: str | None

    model_config = {"from_attributes": True}


class TransactionPage(BaseModel):
    total: int
    items: list[TransactionOut]


class BillOut(BaseModel):
    id: int
    account_id: int
    payee_key: str
    display_name: str
    amount_cents: int
    cadence: str
    next_due: date
    status: str
    confidence: float
    source: str
    occurrences: int
    last_seen: date | None
    stale: bool = False


class BillCreate(BaseModel):
    account_id: int
    display_name: str
    amount_cents: int = Field(gt=0)
    cadence: Cadence
    next_due: date


class BillPatch(BaseModel):
    status: Literal["detected", "confirmed", "dismissed"] | None = None
    display_name: str | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    cadence: Cadence | None = None
    next_due: date | None = None


class IncomeOut(BaseModel):
    id: int
    account_id: int
    payee_key: str
    display_name: str
    cadence: str
    next_expected: date
    trailing_avg_cents: int
    occurrences: int
    status: str

    model_config = {"from_attributes": True}


class IncomePatch(BaseModel):
    status: Literal["detected", "confirmed", "dismissed"] | None = None
    display_name: str | None = None


class DueItemOut(BaseModel):
    bill_id: int
    name: str
    due: date
    amount_cents: int


class WindowOut(BaseModel):
    days: int
    required_cents: int
    headroom_cents: int
    status: str
    due: list[DueItemOut]


class IncomeOutlookOut(BaseModel):
    id: int
    name: str
    next_expected: date
    expected_cents: int
    basis_n: int
    cadence: str
    overdue: bool
    status: str


class ForecastAccountOut(BaseModel):
    id: int
    name: str
    institution: str
    type: str
    balance_cents: int
    as_of: date | None


class ForecastOut(BaseModel):
    as_of: date
    cash_on_hand_cents: int
    accounts: list[ForecastAccountOut]
    windows: list[WindowOut]
    income: list[IncomeOutlookOut]
    pending_review: int


class ImportReceiptOut(BaseModel):
    batch_id: int
    parser: str
    filename: str
    rows_total: int
    rows_added: int
    rows_duplicate: int
    accounts: list[str]


class HealthOut(BaseModel):
    status: str
    app_name: str
    version: str
    data_dir: str
