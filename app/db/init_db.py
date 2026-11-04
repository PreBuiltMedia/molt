"""
Creates tables directly from the SQLAlchemy models.

This is fine pre-launch / early stage. Once you have real customer data in
production, switch to Alembic migrations instead of this -- `create_all`
doesn't know how to alter existing tables, only create missing ones, so
schema changes after go-live need real migrations.

Run with: python -m app.db.init_db
"""
from __future__ import annotations

from app.db.models import Base
from app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created (or already existed).")


if __name__ == "__main__":
    init_db()
