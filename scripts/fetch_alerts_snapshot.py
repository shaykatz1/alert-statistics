"""
Fetch latest alerts from Home Front Command API, upsert into Supabase,
and upload a full snapshot JSON to Supabase Storage for fast frontend loads.

Required env vars:
    SUPABASE_URL         https://xxx.supabase.co
    SUPABASE_SERVICE_KEY service_role secret key
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    print("Install httpx first:  pip install httpx", file=sys.stderr)
    sys.exit(1)

OREF_URL = "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json"
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
STORAGE_BUCKET = "snapshots"
STORAGE_FILE = "alerts_history.json.gz"
PAGE_SIZE = 10_000


def fetch_oref() -> list[dict]:
    res = subprocess.run(
        [
            "curl", "-s", "--max-time", "30",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "-H", "Accept: application/json, text/plain, */*",
            "-H", "Accept-Language: he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "-H", "Referer: https://www.oref.org.il/",
            "-H", "Origin: https://www.oref.org.il",
            OREF_URL,
        ],
        capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(f"curl failed: {res.stderr}")
    payload = res.stdout.lstrip("﻿").strip()
    if not payload:
        raise RuntimeError("Empty response from oref API (IP may be blocked)")
    data = json.loads(payload)
    if not isinstance(data, list):
        raise RuntimeError(f"Expected list, got {type(data).__name__}")
    return data


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


def upsert(client: httpx.Client, rows: list[dict]) -> None:
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
    """Fetch every row from Supabase to build the storage snapshot."""
    all_rows: list[dict] = []
    offset = 0
    print("  Fetching all rows from DB for snapshot...")
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

        # Advance by actual rows returned (may be less than PAGE_SIZE if server caps it)
        offset += len(batch)
        if offset % 10000 == 0 or offset >= total:
            print(f"    {len(all_rows)}/{total}")
        if offset >= total:
            break

    return all_rows


def upload_snapshot(client: httpx.Client, rows: list[dict]) -> None:
    """Upload the full dataset as a gzip-compressed JSON to Supabase Storage."""
    print(f"  Compressing snapshot ({len(rows)} rows)...")
    raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload = gzip.compress(raw, compresslevel=6)
    print(f"  {len(raw)/1024/1024:.1f} MB → {len(payload)/1024/1024:.1f} MB (gzip)")

    resp = client.post(
        f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{STORAGE_FILE}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/gzip",
            "Content-Length": str(len(payload)),
            "x-upsert": "true",
            "Cache-Control": "public, max-age=7200",
        },
        content=payload,
        timeout=120,
    )
    resp.raise_for_status()
    print(f"  Snapshot uploaded — {len(payload)/1024/1024:.1f} MB")


def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching from oref.org.il...")
    try:
        raw = fetch_oref()
        rows = [r for r in (to_row(x) for x in raw) if r]
        print(f"  {len(raw)} records fetched → {len(rows)} valid rows")
    except (SystemExit, Exception) as e:
        print(f"  Warning: could not fetch from oref ({e}) — will still rebuild snapshot from DB.")
        rows = []

    with httpx.Client() as client:
        if rows:
            upsert(client, rows)
            print(f"  Upserted {len(rows)} rows into Supabase.")
        else:
            print("  No new rows to upsert.")

        all_rows = fetch_all_from_db(client)
        upload_snapshot(client, all_rows)

    print("Done.")


if __name__ == "__main__":
    main()
