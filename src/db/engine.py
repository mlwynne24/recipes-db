import sqlite_vec
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from src.config.settings import settings


def _load_sqlite_vec(dbapi_conn, _connection_record):
    sqlite_vec.load(dbapi_conn)


def make_engine() -> Engine:
    engine = create_engine(f"sqlite:///{settings.database_path}")
    event.listen(engine, "connect", _load_sqlite_vec)
    return engine


engine = make_engine()


def get_session():
    with Session(engine) as session:
        yield session
