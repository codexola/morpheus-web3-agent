# Changelog

## 1.1.0 — 2026-09-10

- Neon Postgres via Vercel Marketplace for durable tasks, events, and audit logs.
- Schema auto-migrates on startup; `/health` reports database status.
- Optional Upstash Redis rate limiting (REST) with memory fallback.
- Optional Sentry initialization when `SENTRY_DSN` is configured.
- Docs: `docs/manual-setup.md` for secrets that require manual action.

## 1.0.1 — 2026-09-10

- Harden production reliability: blank RPC env vars no longer wipe defaults.
- SSRF: research URL fetch no longer follows redirects blindly; each hop is revalidated.
- Reject unsupported analytics chains instead of silently using Ethereum.
- Merge LLM findings with static analysis (never discard pattern findings).
- Atomic task idempotency claim; hide internal exception details from clients.
- Standardized validation error responses; constant-time secret compare.
- RPC retries for transient HTTP failures; clarify analytics capability scope.
- Vercel function `maxDuration` via `api/index.py`.

## 1.0.0 — 2026-09-09

- Initial MVP release for Morpheus Protocol registration.
- Endpoints: `/`, `/health`, `/morpheus/verify`, `/capabilities`, `/api/tasks`, `/api/tasks/{id}`, `/callbacks/morpheus`, `/version`.
- Agents: smart_contract_audit, code_security_review, blockchain_analytics, web3_research.
- Idempotent task store, rate limiting, SSRF URL guards, structured security reports.
- Vercel FastAPI deployment entrypoint via `app.main:app`.
