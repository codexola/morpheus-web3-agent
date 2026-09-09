#!/usr/bin/env python3
"""Verify /morpheus/verify deployment blocker."""

from __future__ import annotations

import sys
import time

import httpx


def main(base: str) -> int:
    url = base.rstrip("/") + "/morpheus/verify"
    started = time.time()
    r = httpx.get(url, timeout=10.0)
    elapsed = time.time() - started
    print(f"status={r.status_code} elapsed={elapsed:.3f}s")
    print(r.text[:500])
    if r.status_code != 200:
        return 1
    if elapsed >= 1.0:
        print("WARN: verify slower than 1s target")
    body = r.json()
    if body.get("status") != "ok":
        return 1
    if not body.get("agent", {}).get("online"):
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_prod.py https://your-host")
        sys.exit(2)
    raise SystemExit(main(sys.argv[1]))
