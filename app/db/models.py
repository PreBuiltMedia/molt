"""
SQLAlchemy models.

Design notes:
- API keys are stored as a salted hash, never in plaintext. The raw key is
  shown to the customer exactly once, at creation time.
- `plan` lives on Account, not ApiKey, so a customer can rotate keys without
  losing their plan/billing state.
- UsageEvent is an append-only log, separate from the rate limiter. The rate
  limiter (Redis) answers "are they over their window limit right now"; this
  table answers "what did they actually do" for support, billing disputes,
  and analytics. Don't make the rate limiter read from Postgres on every
  request -- that's what Redis is for.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.config import PlanName


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    plan: Mapped[PlanName] = mapped_column(
        Enum(PlanName, name="plan_name"), default=PlanName.FREE, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Data-broker compliance: when a deletion request is honored, we keep the
    # account row (for billing history) but flag it so all enrichment/search
    # traffic for this account is refused going forward.
    deletion_requested_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = _uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # shown in dashboards, e.g. "ek_live_ab12"
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="api_keys")


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_account_created", "account_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    bucket: Mapped[str] = mapped_column(String(32), nullable=False)  # "search" | "enrich" | "phone"
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
