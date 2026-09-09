#!/usr/bin/env python3
"""Production smoke tests."""

from __future__ import annotations

import sys

import httpx


def main(base: str) -> int:
    base = base.rstrip("/")
    paths = ["/", "/health", "/morpheus/verify", "/capabilities", "/version"]
    ok = True
    with httpx.Client(timeout=30.0) as client:
        for path in paths:
            url = f"{base}{path}"
            try:
                r = client.get(url)
                print(f"{r.status_code} GET {path}")
                if r.status_code != 200:
                    ok = False
            except Exception as exc:
                print(f"ERR  GET {path}: {exc}")
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
