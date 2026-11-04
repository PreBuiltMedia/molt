# EnrichAPI (working name)

A headless, agent-first B2B contact enrichment API: flat-rate pricing, no UI,
built to be called from an agent (Claude/MCP, ChatGPT, or REST) rather than
clicked through a dashboard.

## Why this structure

- **No scraping of any specific competitor is included here.** This scaffold
  gives you the pipeline shape (search → infer → verify → score → return) and
  leaves the actual data sources (your own crawlers, licensed datasets,
  carrier APIs) as pluggable providers you configure.
- **Flat-rate, rate-limited plans** instead of credit metering, matching the
  agent-native pricing model (agents want a key + a ceiling, not a credit
  counter).
- **MCP server included from day one**, since agent access via Claude/MCP is
  the primary surface, with REST as a secondary interface.

## Layout

```
app/
  main.py                 FastAPI app entrypoint
  core/
    config.py             Settings (env vars, plan tiers, rate limits)
    security.py           API key auth + plan lookup
    rate_limit.py          Sliding-window rate limiter (per-plan)
  services/
    pattern_inference.py  Name + domain -> candidate email patterns
    email_verify.py       MX / SMTP / catch-all / disposable checks
    risk_score.py         Combines verification signals into A-F grade
    providers/
      base.py              Abstract "data provider" interface
      stub_provider.py     Example in-memory provider (replace with real source)
  api/
    v1/
      people.py            /v1/people/search
      contacts.py          /v1/contacts/enrich
      email.py              /v1/email/verify
      account.py            /v1/account (usage, plan, billing - no token cost)
  models/
    schemas.py              Pydantic request/response models
mcp/
  server.py                 MCP server exposing the same operations as tools
tests/
  test_email_verify.py
  test_rate_limit.py
requirements.txt
.env.example
```

## Running it

**With Docker (recommended — brings up Postgres + Redis too):**

```bash
cp .env.example .env
docker compose up --build
python -m app.db.init_db   # creates tables (run once, or after model changes)
```

**Without Docker** (you provide Postgres + Redis yourself):

```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env   # fill in DATABASE_URL / REDIS_URL for your own instances
python -m app.db.init_db
uvicorn app.main:app --reload --port 8000
```

MCP server (stdio, for local Claude Desktop / Claude Code testing):

```bash
python -m mcp.server
```

### First signup, locally

```bash
curl -X POST localhost:8000/v1/signup -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
# -> returns {"account_id": "...", "plan": "free", "api_key": "ek_live_..."}
# Save that api_key -- it's shown exactly once.

curl -X POST localhost:8000/v1/contacts/enrich -H "X-API-Key: ek_live_..." \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Jane", "last_name": "Doe", "company_domain": "example.com"}'
```

## Deploying to Railway

1. Push this repo to GitHub, then in Railway: New Project → Deploy from GitHub repo.
2. Add two plugins to the project: **PostgreSQL** and **Redis**. Railway
   auto-injects `DATABASE_URL` and `REDIS_URL` into your service — you don't
   need to set those manually.
3. In your service's Variables tab, set everything else from `.env.example`
   that isn't auto-provided: `DEV_API_KEY` (or remove it once you have real
   accounts), `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, the three
   `STRIPE_PRICE_ID_*` values, and **`EMAIL_VERIFICATION_PROVIDER=zerobounce`**
   (or `kickbox`) plus that provider's API key. Do not set it to `raw_smtp`
   on Railway — outbound port 25 is blocked there, so it won't work.
4. After first deploy, open a shell on the Railway service (or run once
   locally pointed at the Railway database via `railway run`) and execute
   `python -m app.db.init_db` to create tables.
5. Point your Stripe webhook endpoint at `https://<your-railway-domain>/v1/billing/webhook`.

`railway.toml` in this repo already configures the Dockerfile build and a
`/health` healthcheck — Railway should pick it up automatically.

## What's real vs. a placeholder here

- Email **syntax/disposable/role-based/free-webmail/MX checks**: real, local,
  working logic, no third party needed.
- Email **deliverability + catch-all check**: real, pluggable. Implemented
  for ZeroBounce and Kickbox (`app/services/email_providers/`), plus a
  `raw_smtp` fallback for local dev only. Swap providers with one env var
  (`EMAIL_VERIFICATION_PROVIDER`) — no code changes needed. Add another
  provider by implementing `EmailVerificationProvider` in a new file and
  registering it in `factory.py`.
- Email **pattern inference**: real, working logic (common pattern set + domain
  confidence scoring you can pre-seed from your own data).
- **Accounts, API keys, usage events**: real, Postgres-backed. Keys are
  stored as salted hashes, never in plaintext.
- **Rate limiting**: real. `app/core/rate_limit.py` (in-memory) is the
  dev/test path; `app/core/redis_rate_limit.py` is the production path —
  wire `enforce_rate_limit` to call the Redis version before deploying
  behind more than one worker process.
- **Stripe billing**: real integration shape (checkout session creation +
  signed webhook handling that updates `Account.plan`). You still need to:
  create the actual Products/Prices in your Stripe dashboard, set the price
  IDs in `.env`, and point a live webhook endpoint at `/v1/billing/webhook`.
- **Compliance**: `/v1/compliance/delete-account` is real and locks the
  account out. `/v1/compliance/suppress-contact` is a deliberate stub —
  it raises `NotImplementedError` on purpose so it can't ship by accident
  before it's wired to a real suppression list that your data provider
  actually checks.
- **People/company search**: a stub provider with fake sample records. You
  plug in your own data source(s) behind the `providers/base.py` interface —
  web harvesting pipeline, licensed dataset, your own crawler, etc. This repo
  does not include a scraper for any specific site or competitor.
- **Mobile number lookups**: stubbed as a call to a generic carrier-lookup
  interface (e.g., Twilio Lookup / NumVerify) — you'll drop in real API keys.

## Next steps (not yet built)

1. A real `providers/` implementation backed by your actual data pipeline
   (the big one — see the "getting data" conversation separately)
2. Switch `app/db/init_db.py`'s `create_all` to Alembic migrations before
   you have real production data to protect
3. Carrier-lookup provider implementation (Twilio Lookup / NumVerify) behind
   `carrier_lookup_provider` in config
4. API key rotation/revocation endpoint (model supports it; no route yet)
5. Admin/ops dashboard (even a minimal internal one) for support to look up
   an account's usage and plan without querying Postgres directly
6. Production deploy target (Fly.io, Render, ECS, etc.) + CI
