# Changelog

## 1.2.1 — 2026-09-10

- Production hardening for Arena + Morpheus live ops.
- OpenAI-compat: trailing-slash routes, SSE stream, null content, OpenAI error shape, api-key headers.
- Verify reflects database health; stale PROCESSING reclaim; callback delivery.
- Gate `/sentry-debug` in production; `.vercelignore`; version sync.

## 1.2.0 — 2026-09-10

- OpenAI-compatible Arena endpoint (`POST /`, `/v1/chat/completions`) to fix HTTP 405.

## 1.1.0 — 2026-09-10

- Neon Postgres durable task store and integration wiring.

## 1.0.1 — 2026-09-10

- Harden production reliability and security.

## 1.0.0 — 2026-09-09

- Initial MVP release for Morpheus Protocol registration.
