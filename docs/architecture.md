# Architecture

## Overview

API-first Morpheus agent on FastAPI / Vercel.

```
Morpheus → https://<stable-host>
              ├── /morpheus/verify
              ├── /health
              └── /api/tasks → adapter → InternalTask → router → agents → JSON result
```

## Layers

1. **Morpheus integration** — `/morpheus/verify`, task request adapter, callbacks
2. **Internal API** — validated `InternalTask` model
3. **Task router** — deterministic capability routing
4. **Agent engines** — smart contract, code review, analytics, research
5. **External tools** — OpenAI (optional), EVM/Solana RPC, HTTP fetch (SSRF-guarded)

## Hybrid compute

MVP static analysis runs as regex/AST-light patterns inside the Vercel function so the agent works without native `solc`/`slither` binaries.

Heavy Slither/solc workers can be added later behind the same public API.

## Persistence

Default store is in-process memory with external_task_id idempotency.

Set `DATABASE_URL` in a later release for PostgreSQL-backed history across instances.
