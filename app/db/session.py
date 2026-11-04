from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _normalize_database_url(url: str) -> str:
    """
    Railway (and Heroku, Render, etc.) typically inject DATABASE_URL as
    postgres://... or postgresql://..., but SQLAlchemy with the psycopg3
    driver needs postgresql+psycopg://... explicitly. Without this, a
    Railway deploy will connect fine locally (where .env has the full
    scheme already) and then fail immediately in production with a
    confusing driver error.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_normalize_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
