# Operations

## Environments

- Development — local `.env`
- Preview — Vercel preview deployments
- Production — stable custom domain preferred

## Deployment

```bash
vercel --prod
```

Required production env vars (minimum):

- `AGENT_NAME`, `AGENT_VERSION`
- `OPENAI_API_KEY` (optional but recommended)
- RPC URLs as needed
- `MORPHEUS_SHARED_SECRET` if authenticating inbound calls

Never set private keys / seed phrases.

## Smoke tests

```bash
python scripts/smoke_test.py https://your-deployment.vercel.app
python scripts/verify_prod.py https://your-deployment.vercel.app
```

## Rollback

Use Vercel dashboard Instant Rollback to the previous production deployment if health/verify fails.

## Alerts (suggested)

- `/health` fails twice
- 5xx > 5% for 5 minutes
- p95 latency > 30s
