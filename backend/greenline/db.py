"""Engine/session wiring. The DB file lives in the data dir (decision 0010)."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .models import SCHEMA_VERSION, Base, Meta


def make_engine(settings: Settings) -> Engine:
    db_path: Path = settings.db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if session.scalar(select(Meta).where(Meta.key == "schema_version")) is None:
            session.add(Meta(key="schema_version", value=SCHEMA_VERSION))
            session.commit()


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
