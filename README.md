# Web3Dev AI — Morpheus Protocol Agent

API-first autonomous Web3 development agent for the Morpheus marketplace.

## Capabilities (MVP)

| Capability | Description |
|---|---|
| `smart_contract_audit` | Solidity security analysis (patterns + optional LLM) |
| `code_security_review` | Source security review (Python/JS/TS/Java/Solidity) |
| `blockchain_analytics` | Wallet/tx/token analysis (ETH, Base, Arbitrum, Polygon, Solana) |
| `web3_research` | Structured Web3/DeFi research reports |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service identity |
| GET | `/health` | Liveness (<500ms, no LLM) |
| GET | `/morpheus/verify` | Morpheus capability verification |
| GET | `/capabilities` | Declared capabilities |
| POST | `/api/tasks` | Submit a task |
| GET | `/api/tasks/{task_id}` | Poll task status/result |
| POST | `/callbacks/morpheus` | Inbound Morpheus callbacks |
| GET | `/version` | Version / commit diagnostics |

## Local development

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

## Deploy (Vercel)

```bash
vercel --prod
```

Neon Postgres is provisioned via the Vercel Marketplace (`DATABASE_URL`).  
See `docs/manual-setup.md` for secrets you must add yourself (OpenAI, Sentry, Upstash terms, etc.).

## Security notes

- Never store wallet private keys or seed phrases in Vercel.
- Use only a public payout address for Morpheus payments.
- Task content is treated as untrusted data (prompt-injection resistant prompts).
- A2A paid outbound calls are disabled by default.

## Tests

```bash
pytest -q
```

## Architecture

See `docs/architecture.md` and `docs/morpheus.md`.
