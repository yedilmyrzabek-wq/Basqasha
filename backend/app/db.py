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
engine = create_engine(_url(), pool_pre_ping=True, pool_size=4, max_overflow=3, pool_recycle=1800)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


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
    """FastAPI dependency."""
    with session_scope() as s:
        yield s
