#!/usr/bin/env python3
"""
Upload the locally-cached historical data (data/historical_monthly.json)
to Supabase and rebuild the Storage snapshot.

Run this after fetch_historical_correct.py, or whenever you have a local
JSON file you want to push to the database.

Required env vars:
    SUPABASE_URL         https://xxx.supabase.co
    SUPABASE_SERVICE_KEY service_role secret key

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python3 scripts/merge_weekly_data.py
"""

from __future__ import annotations

import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

MONTHLY_FILE = Path("data/historical_monthly.json")
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
STORAGE_FILE = "alerts_history.json.gz"
PAGE_SIZE = 1000
BATCH_SIZE = 5_000


def normalize_date(s: str) -> str:
    s = s.replace(" ", "T")
    parts = s.split("T")
    if len(parts) == 2:
        tp = parts[1].split(":")
        if len(tp) >= 3:
            tp[2] = "00"
            return f"{parts[0]}T{':'.join(tp)}"
    return s


def to_row(r: dict) -> dict | None:
    ad = r.get("alertDate")
    title = r.get("category_desc") or r.get("title", "")
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


def upsert_batch(client: httpx.Client, rows: list[dict]) -> None:
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


def fetch_all_from_db(client: httpx.Client) -> list[dict]:
    all_rows: list[dict] = []
    offset = 0
    print("  Reading all rows from DB for snapshot...")
    while True:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/alerts",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Range-Unit": "items",
                "Range": f"{offset}-{offset + PAGE_SIZE - 1}",
                "Prefer": "count=exact",
            },
            params={"select": "alert_date,title,settlement,category", "order": "alert_date.desc"},
            timeout=60,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_rows.extend(batch)
        content_range = resp.headers.get("Content-Range", "")
        total = int(content_range.split("/")[1]) if "/" in content_range else len(all_rows)
        offset += len(batch)
        if offset % 50000 == 0 or offset >= total:
            print(f"    {len(all_rows)}/{total}")
        if offset >= total:
            break
    return all_rows


def upload_snapshot(client: httpx.Client, rows: list[dict]) -> None:
    print(f"  Compressing {len(rows)} rows...")
    raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = gzip.compress(raw, compresslevel=6)
    print(f"  {len(raw)/1024/1024:.1f} MB → {len(payload)/1024/1024:.1f} MB")
    resp = client.post(
        f"{SUPABASE_URL}/storage/v1/object/snapshots/{STORAGE_FILE}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/gzip",
            "Content-Length": str(len(payload)),
            "x-upsert": "true",
            "Cache-Control": "public, max-age=7200",
        },
        content=payload,
        timeout=180,
    )
    resp.raise_for_status()
    print("  Snapshot uploaded.")


def main() -> None:
    if not MONTHLY_FILE.exists():
        print(f"File not found: {MONTHLY_FILE}")
        print("Run fetch_historical_correct.py first.")
        return

    raw = json.loads(MONTHLY_FILE.read_text(encoding="utf-8"))
    rows = [r for r in (to_row(a) for a in raw) if r]
    print(f"Loaded {len(raw)} records from {MONTHLY_FILE} → {len(rows)} valid rows")

    print(f"Upserting to Supabase...")
    with httpx.Client() as client:
        for i in range(0, len(rows), BATCH_SIZE):
            upsert_batch(client, rows[i: i + BATCH_SIZE])
            print(f"  {min(i + BATCH_SIZE, len(rows))}/{len(rows)}")

        print("\nRebuilding snapshot...")
        all_rows = fetch_all_from_db(client)
        upload_snapshot(client, all_rows)

    print(f"\nDone — {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
