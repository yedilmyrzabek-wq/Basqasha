"""SQLAlchemy engine/session on Supabase Postgres (Session pooler :5432)."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _url() -> str:
    url = get_settings().database_url
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    return url


# API and worker each hold a pool; keep the sum under the Supavisor session-mode limit (15).
# The pooler is ~235 ms away, so round trips are the cost: no pre-ping on every checkout
# (connections are recycled after 5 min instead, and a dropped one is invalidated on error),
# and read-only requests run in autocommit mode (no BEGIN/COMMIT round trips).
engine = create_engine(_url(), pool_pre_ping=False, pool_size=4, max_overflow=3, pool_recycle=300)
read_engine = engine.execution_options(isolation_level="AUTOCOMMIT")
SessionLocal = sessionmaker(engine, expire_on_commit=False)
ReadSession = sessionmaker(read_engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency (read-write transaction)."""
    with session_scope() as s:
        yield s


def get_read_db() -> Iterator[Session]:
    """FastAPI dependency for GET endpoints (autocommit, no transaction round trips)."""
    s = ReadSession()
    try:
        yield s
    finally:
        s.close()
