#!/usr/bin/env python3
"""Production smoke tests including Arena OpenAI surface."""

from __future__ import annotations

import sys

import httpx


def main(base: str) -> int:
    base = base.rstrip("/")
    ok = True
    with httpx.Client(timeout=60.0, follow_redirects=False) as client:
        for path in ["/", "/health", "/morpheus/verify", "/capabilities", "/version", "/v1/models"]:
            r = client.get(f"{base}{path}")
            print(f"{r.status_code} GET {path}")
            if r.status_code != 200:
                ok = False

        for path in ["/", "/v1/chat/completions", "/v1/chat/completions/"]:
            r = client.post(
                f"{base}{path}",
                json={
                    "model": "web3dev-ai",
                    "messages": [{"role": "user", "content": "smoke ping"}],
                    "stream": False,
                },
            )
            print(f"{r.status_code} POST {path}")
            if r.status_code != 200:
                ok = False
            elif path.endswith("/") and r.is_redirect:
                print("ERR unexpected redirect on trailing slash")
                ok = False

        payload = {
            "task_id": "smoke_research_1",
            "capability": "web3_research",
            "description": "Smoke test research on Ethereum staking",
        }
        r = client.post(f"{base}/api/tasks", json=payload)
        print(f"{r.status_code} POST /api/tasks")
        if r.status_code != 200:
            ok = False
        else:
            task_id = r.json().get("task_id")
            if task_id:
                g = client.get(f"{base}/api/tasks/{task_id}")
                print(f"{g.status_code} GET /api/tasks/{{id}}")
                if g.status_code != 200:
                    ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/smoke_test.py https://your-host")
        sys.exit(2)
    raise SystemExit(main(sys.argv[1]))
