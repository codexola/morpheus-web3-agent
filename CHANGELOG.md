# Changelog

## 1.0.0 — 2026-09-09

- Initial MVP release for Morpheus Protocol registration.
- Endpoints: `/`, `/health`, `/morpheus/verify`, `/capabilities`, `/api/tasks`, `/api/tasks/{id}`, `/callbacks/morpheus`, `/version`.
- Agents: smart_contract_audit, code_security_review, blockchain_analytics, web3_research.
- Idempotent task store, rate limiting, SSRF URL guards, structured security reports.
- Vercel FastAPI deployment entrypoint via `app.main:app`.
