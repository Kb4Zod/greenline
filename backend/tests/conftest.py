"""Shared fixtures. Synthetic data only (decision 0011); fixed clocks only."""

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from greenline.config import Settings
from greenline.db import init_db, make_engine, make_session_factory
from greenline.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"

# The synthetic statements span 2026-04-01 .. 2026-06-30; date-sensitive
# assertions pin "today" instead of reading the wall clock.
TODAY = date(2026, 6, 12)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path, _env_file=None)


@pytest.fixture
def session(settings: Settings):
    engine = make_engine(settings)
    init_db(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        yield session


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def upload(client: TestClient, name: str):
    return client.post(
        "/api/imports",
        files={"file": (name, fixture_bytes(name), "text/csv")},
    )
