#!/usr/bin/env python3
"""Apply Neon Postgres schema migrations."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


async def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    _load_env_file(root / ".env.local")
    _load_env_file(root / ".env")

    from app.core.config import get_settings
    from app.db.connection import close_pool, init_schema, ping

    get_settings.cache_clear()
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    ok = await init_schema()
    alive = await ping()
    await close_pool()
    print(f"schema={ok} ping={alive}")
    return 0 if ok and alive else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
