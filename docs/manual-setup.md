# Manual setup checklist

## Already configured remotely

- Neon Postgres (`morpheus-web3-db`) on Vercel
- `OPENAI_API_KEY` (Production / Preview / Development)
- `SENTRY_DSN` (Production / Preview / Development)
- FastAPI Sentry SDK (errors + tracing) with `/sentry-debug` verification route

## Still requires your action

### 1. Upstash Redis terms (optional shared rate limits)

1. Open https://vercel.com/codexolas-projects/~/integrations/accept-terms/upstash?source=cli
2. Accept terms
3. Run:

```bash
vercel install upstash/upstash-kv --name morpheus-web3-kv --plan free -e production -e preview -e development --non-interactive
vercel --prod
```

### 2. Custom domain (recommended for Morpheus)

Vercel → Project → Settings → Domains → add e.g. `agent.yourdomain.com`

### 3. Morpheus registration fields

- Endpoint: `https://morpheus-web3-agent.vercel.app` (or your custom domain)
- Payout: **public** wallet address only
- Optional: set `MORPHEUS_SHARED_SECRET` in Vercel after you choose a secret

### 4. Paid RPC providers (optional)

Public RPCs work. For higher reliability set `ETH_RPC_URL`, `BASE_RPC_URL`, `ARBITRUM_RPC_URL`, `POLYGON_RPC_URL`, `SOLANA_RPC_URL`.

### 5. Security note

API keys pasted in chat should be **rotated** in OpenAI / Sentry when convenient, since chat history may retain them.
