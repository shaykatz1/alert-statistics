"""
One-time migration: upload existing alerts_history.json to Supabase.

Usage:
    SUPABASE_URL=https://xxx.supabase.co \
    SUPABASE_SERVICE_KEY=your_service_role_key \
    python3 scripts/migrate_to_supabase.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx first:  pip install httpx", file=sys.stderr)
    sys.exit(1)

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
JSON_PATH = Path("docs/data/alerts_history.json")
BATCH_SIZE = 5_000


def normalize_date(s: str) -> str:
    """Return ISO-8601 with T separator and seconds zeroed."""
    s = s.replace(" ", "T")
    parts = s.split("T")
    if len(parts) == 2:
        time_parts = parts[1].split(":")
        if len(time_parts) >= 3:
            time_parts[2] = "00"
            return f"{parts[0]}T{':'.join(time_parts)}"
    return s


def to_row(r: dict) -> dict | None:
    ad = r.get("alertDate")
    title = r.get("title", "")
    settlement = r.get("data", "")
    category = r.get("category")
    if not ad or not title or not settlement or category is None:
        return None
    return {
        "alert_date": normalize_date(ad),
        "title": title,
        "settlement": str(settlement).strip(),
        "category": int(category),
    }


def upsert_batch(client: httpx.Client, rows: list[dict]) -> int:
    resp = client.post(
        f"{SUPABASE_URL}/rest/v1/alerts",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
        },
        json=rows,
        timeout=60,
    )
    resp.raise_for_status()
    return len(rows)


def main() -> None:
    print(f"Loading {JSON_PATH}...")
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    rows = [r for r in (to_row(x) for x in raw) if r]
    print(f"  {len(raw)} records → {len(rows)} valid rows")

    with httpx.Client() as client:
        total = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            upserted = upsert_batch(client, batch)
            total += upserted
            pct = (i + len(batch)) / len(rows) * 100
            print(f"  {i + len(batch):>7}/{len(rows)} ({pct:.1f}%)  +{upserted}")
            # Tiny pause to be kind to the free-tier API
            time.sleep(0.2)

    print(f"\nDone — {total} rows uploaded.")


if __name__ == "__main__":
    main()
