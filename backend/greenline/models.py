"""SQLAlchemy models — SPEC-M1 §2. Amounts are integer cents, dates ISO."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA_VERSION = "1"


class Base(DeclarativeBase):
    pass


class Meta(Base):
    __tablename__ = "meta"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("name", "institution"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    institution: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="checking")  # checking | savings
    balance_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    balance_as_of: Mapped[date | None] = mapped_column(Date, nullable=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    imported_at: Mapped[datetime] = mapped_column(DateTime)
    parser: Mapped[str] = mapped_column(String)
    rows_total: Mapped[int] = mapped_column(Integer)
    rows_added: Mapped[int] = mapped_column(Integer)
    rows_duplicate: Mapped[int] = mapped_column(Integer)
    date_min: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_max: Mapped[date | None] = mapped_column(Date, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"))
    posted_date: Mapped[date] = mapped_column(Date, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)  # signed: debit < 0
    description: Mapped[str] = mapped_column(String)
    payee_key: Mapped[str] = mapped_column(String, index=True)
    category_raw: Mapped[str | None] = mapped_column(String, nullable=True)
    balance_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dedup_key: Mapped[str] = mapped_column(String, unique=True)


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    payee_key: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    amount_cents: Mapped[int] = mapped_column(Integer)  # positive magnitude
    cadence: Mapped[str] = mapped_column(String)
    next_due: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, default="detected")  # detected|confirmed|dismissed
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String, default="detected")  # detected|manual
    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[date | None] = mapped_column(Date, nullable=True)


class IncomeStream(Base):
    __tablename__ = "income_streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    payee_key: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    cadence: Mapped[str] = mapped_column(String)
    next_expected: Mapped[date] = mapped_column(Date)
    trailing_avg_cents: Mapped[int] = mapped_column(Integer)
    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="detected")
