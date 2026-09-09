# Morpheus integration notes

## Important limitation

Morpheus publicly documents its **outbound** marketplace API (submit/poll/capabilities/health) more clearly than the exact inbound request schema sent to operator agents.

This agent therefore:

1. Exposes `/morpheus/verify` with a conservative identity/capabilities payload
2. Accepts flexible task fields (`task_id` / `external_task_id` / `id`, `input` / `payload` / `data`)
3. Normalizes everything into an internal `InternalTask`
4. Is ready to adjust the Morpheus adapter after live verification reveals extra requirements

## Registration fields (recommended)

- **Agent Name:** Web3Dev AI
- **Endpoint:** `https://agent.yourdomain.com` (preferred) or the Vercel production URL
- **Services (MVP):** Smart Contract Audit, Code Security Review, Blockchain Analytics, Web3 Research
- **Payout:** public wallet address only

## Directions

| Direction | Meaning |
|---|---|
| Incoming | Morpheus → this agent endpoint |
| Outgoing | This agent → `MORPHEUS_API_URL` A2A API (disabled for paid calls in MVP) |

## Compatibility log

| Date | Event | Result |
|---|---|---|
| 2026-09-09 | Initial implementation | Local/contract tests pass; awaiting live Morpheus verify |
