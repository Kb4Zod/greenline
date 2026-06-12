"""FastAPI app (SPEC-M1 §7). Localhost-only, single user, no auth, no telemetry."""

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import __version__
from .config import Settings
from .db import init_db, make_engine, make_session_factory
from .detection import run_detection
from .forecast import bill_is_stale, build_forecast
from .importing import ParseFailure, UnsupportedFormat, import_statement
from .models import Account, Bill, ImportBatch, IncomeStream, Transaction
from .util import normalize_payee
from . import schemas as s


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings)
    init_db(engine)
    session_factory = make_session_factory(engine)

    app = FastAPI(title=settings.app_name, version=__version__)
    app.state.settings = settings

    # Dev-time only: the Vite dev server origin. The packaged app serves the
    # built frontend from this same origin and needs no CORS at all.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    Db = Annotated[Session, Depends(get_session)]

    # ---- health ----------------------------------------------------------

    @app.get("/api/health", response_model=s.HealthOut)
    def health() -> s.HealthOut:
        return s.HealthOut(
            status="ok",
            app_name=settings.app_name,
            version=__version__,
            data_dir=str(settings.resolved_data_dir()),
        )

    # ---- imports ---------------------------------------------------------

    @app.post("/api/imports", response_model=s.ImportReceiptOut, status_code=201)
    async def create_import(file: UploadFile, db: Db) -> s.ImportReceiptOut:
        data = await file.read()
        # Never trust/keep a client path; basename only.
        filename = Path(file.filename or "statement.csv").name
        try:
            receipt = import_statement(db, filename, data)
        except UnsupportedFormat as exc:
            raise HTTPException(
                422,
                detail={
                    "message": "Unsupported statement format.",
                    "found_headers": exc.found_headers,
                },
            )
        except ParseFailure as exc:
            raise HTTPException(
                422,
                detail={
                    "message": "Statement contains invalid rows; nothing was imported.",
                    "rows": [e.model_dump() for e in exc.errors],
                },
            )
        run_detection(db, settings)
        return s.ImportReceiptOut(**receipt.model_dump())

    @app.get("/api/imports", response_model=list[s.ImportBatchOut])
    def list_imports(db: Db) -> list[ImportBatch]:
        return list(
            db.scalars(select(ImportBatch).order_by(ImportBatch.imported_at.desc()))
        )

    # ---- accounts --------------------------------------------------------

    @app.get("/api/accounts", response_model=list[s.AccountOut])
    def list_accounts(db: Db) -> list[Account]:
        return list(db.scalars(select(Account).order_by(Account.id)))

    @app.patch("/api/accounts/{account_id}", response_model=s.AccountOut)
    def patch_account(account_id: int, patch: s.AccountPatch, db: Db) -> Account:
        account = db.get(Account, account_id)
        if account is None:
            raise HTTPException(404, "account not found")
        if patch.name is not None:
            account.name = patch.name
        if patch.type is not None:
            account.type = patch.type
        db.commit()
        return account

    # ---- transactions ----------------------------------------------------

    @app.get("/api/transactions", response_model=s.TransactionPage)
    def list_transactions(
        db: Db,
        account_id: int | None = None,
        date_from: Annotated[date | None, Query(alias="from")] = None,
        date_to: Annotated[date | None, Query(alias="to")] = None,
        q: str | None = None,
        limit: int = Query(50, le=500),
        offset: int = 0,
    ) -> s.TransactionPage:
        stmt = select(Transaction)
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if date_from is not None:
            stmt = stmt.where(Transaction.posted_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Transaction.posted_date <= date_to)
        if q:
            stmt = stmt.where(Transaction.description.icontains(q))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = db.scalars(
            stmt.order_by(Transaction.posted_date.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return s.TransactionPage(
            total=total, items=[s.TransactionOut.model_validate(r) for r in rows]
        )

    # ---- bills -----------------------------------------------------------

    def _bill_out(bill: Bill, today: date) -> s.BillOut:
        return s.BillOut(
            id=bill.id,
            account_id=bill.account_id,
            payee_key=bill.payee_key,
            display_name=bill.display_name,
            amount_cents=bill.amount_cents,
            cadence=bill.cadence,
            next_due=bill.next_due,
            status=bill.status,
            confidence=bill.confidence,
            source=bill.source,
            occurrences=bill.occurrences,
            last_seen=bill.last_seen,
            stale=bill.status == "confirmed" and bill_is_stale(bill, today),
        )

    @app.get("/api/bills", response_model=list[s.BillOut])
    def list_bills(db: Db, status: str | None = None) -> list[s.BillOut]:
        stmt = select(Bill)
        if status is not None:
            stmt = stmt.where(Bill.status == status)
        today = date.today()
        bills = sorted(
            db.scalars(stmt),
            key=lambda b: (b.status != "detected", -b.confidence, b.display_name),
        )
        return [_bill_out(b, today) for b in bills]

    @app.post("/api/bills", response_model=s.BillOut, status_code=201)
    def create_bill(body: s.BillCreate, db: Db) -> s.BillOut:
        if db.get(Account, body.account_id) is None:
            raise HTTPException(422, "unknown account_id")
        bill = Bill(
            account_id=body.account_id,
            payee_key=normalize_payee(body.display_name),
            display_name=body.display_name,
            amount_cents=body.amount_cents,
            cadence=body.cadence,
            next_due=body.next_due,
            status="confirmed",
            confidence=1.0,
            source="manual",
            occurrences=0,
            last_seen=None,
        )
        db.add(bill)
        db.commit()
        return _bill_out(bill, date.today())

    @app.patch("/api/bills/{bill_id}", response_model=s.BillOut)
    def patch_bill(bill_id: int, patch: s.BillPatch, db: Db) -> s.BillOut:
        bill = db.get(Bill, bill_id)
        if bill is None:
            raise HTTPException(404, "bill not found")
        for field in ("status", "display_name", "amount_cents", "cadence", "next_due"):
            value = getattr(patch, field)
            if value is not None:
                setattr(bill, field, value)
        db.commit()
        return _bill_out(bill, date.today())

    @app.delete("/api/bills/{bill_id}", status_code=204)
    def delete_bill(bill_id: int, db: Db) -> None:
        bill = db.get(Bill, bill_id)
        if bill is None:
            raise HTTPException(404, "bill not found")
        db.delete(bill)
        db.commit()

    # ---- income ----------------------------------------------------------

    @app.get("/api/income", response_model=list[s.IncomeOut])
    def list_income(db: Db) -> list[IncomeStream]:
        return list(db.scalars(select(IncomeStream).order_by(IncomeStream.id)))

    @app.patch("/api/income/{stream_id}", response_model=s.IncomeOut)
    def patch_income(stream_id: int, patch: s.IncomePatch, db: Db) -> IncomeStream:
        stream = db.get(IncomeStream, stream_id)
        if stream is None:
            raise HTTPException(404, "income stream not found")
        if patch.status is not None:
            stream.status = patch.status
        if patch.display_name is not None:
            stream.display_name = patch.display_name
        db.commit()
        return stream

    # ---- forecast ----------------------------------------------------------

    @app.get("/api/forecast", response_model=s.ForecastOut)
    def forecast(
        db: Db,
        as_of: date | None = Query(
            None, description="Override 'today' (testing/demo convenience)."
        ),
    ) -> s.ForecastOut:
        result = build_forecast(db, settings, as_of or date.today())
        return s.ForecastOut.model_validate(asdict(result))

    return app


def run() -> None:
    """Entry point for `python -m greenline.main` / the launch script."""
    import uvicorn

    settings = Settings()
    uvicorn.run(
        create_app(settings),
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )


if __name__ == "__main__":
    run()
