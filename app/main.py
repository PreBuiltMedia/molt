from __future__ import annotations

from fastapi import FastAPI

from app.api.v1 import account, billing, compliance, contacts, email, people, signup
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Headless B2B contact enrichment API, built for agent access.",
    version="0.1.0",
)

app.include_router(signup.router)
app.include_router(billing.router)
app.include_router(people.router)
app.include_router(contacts.router)
app.include_router(email.router)
app.include_router(account.router)
app.include_router(compliance.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
