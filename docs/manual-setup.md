# Manual setup checklist (secrets you must add)

This project auto-provisioned **Neon Postgres** on Vercel. Remaining items need your credentials or browser approval.

## Already done (no action)

- Neon Postgres (`morpheus-web3-db`) connected to production/preview/development
- `DATABASE_URL` and related Postgres env vars injected by Vercel
- Durable task store, schema bootstrap on startup, health DB check
- Optional Sentry wiring (activates when DSN is set)
- Optional Upstash Redis rate-limit client (activates when REST env vars exist)

## You must add manually

### 1. OpenAI API key (strongly recommended)

Vercel Dashboard → Project `morpheus-web3-agent` → Settings → Environment Variables:

| Name | Value | Environments |
|---|---|---|
| `OPENAI_API_KEY` | your OpenAI secret key | Production, Preview, Development |

Or CLI:

```bash
echo YOUR_KEY | vercel env add OPENAI_API_KEY production --yes
echo YOUR_KEY | vercel env add OPENAI_API_KEY preview --yes
echo YOUR_KEY | vercel env add OPENAI_API_KEY development --yes
vercel --prod
```

Without this key, pattern-based audits still work; LLM enrichment/research quality is limited.

### 2. Upstash Redis terms (optional but recommended for shared rate limits)

Install was blocked pending marketplace terms acceptance:

1. Open: https://vercel.com/codexolas-projects/~/integrations/accept-terms/upstash?source=cli
2. Accept Upstash / Vercel marketplace terms
3. Run:

```bash
vercel install upstash/upstash-kv --name morpheus-web3-kv --plan free -e production -e preview -e development --non-interactive
vercel --prod
```

Until then, rate limiting uses per-instance memory (still functional).

### 3. Sentry DSN (optional monitoring)

| Name | Value |
|---|---|
| `SENTRY_DSN` | from https://sentry.io project settings |

```bash
echo YOUR_DSN | vercel env add SENTRY_DSN production --yes
vercel --prod
```

### 4. Morpheus shared secret (optional hardening)

After Morpheus registration, if you want inbound auth:

| Name | Value |
|---|---|
| `MORPHEUS_SHARED_SECRET` | shared secret you configure with Morpheus |
| `CALLBACK_SHARED_SECRET` | optional callback secret |

Send header: `X-Morpheus-Secret: <value>`

### 5. Paid RPC providers (optional reliability)

Public RPCs work for MVP. For production volume, set:

- `ETH_RPC_URL`
- `BASE_RPC_URL`
- `ARBITRUM_RPC_URL`
- `POLYGON_RPC_URL`
- `SOLANA_RPC_URL`

Providers: Alchemy, Infura, QuickNode, Helius (Solana).

### 6. Custom domain (recommended for Morpheus endpoint)

Vercel → Project → Settings → Domains → add e.g. `agent.yourdomain.com`  
Then register that hostname in Morpheus instead of `*.vercel.app`.

### 7. Payout address

Morpheus registration form only — use your **public** wallet address. Never put private keys in Vercel.
