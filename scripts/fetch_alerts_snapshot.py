"""
Fetch latest alerts from Home Front Command API and upsert into Supabase.

Required env vars:
    SUPABASE_URL         https://xxx.supabase.co
    SUPABASE_SERVICE_KEY service_role secret key
"""
from __future__ import annotations

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
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(f"curl failed: {res.stderr}", file=sys.stderr)
        raise SystemExit(1)

    payload = res.stdout.lstrip("﻿").strip()
    if not payload:
        print("Empty response from oref API", file=sys.stderr)
        raise SystemExit(1)

    data = json.loads(payload)
    if not isinstance(data, list):
        print(f"Expected list, got {type(data).__name__}", file=sys.stderr)
        raise SystemExit(1)
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


def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching from oref.org.il...")
    raw = fetch_oref()
    rows = [r for r in (to_row(x) for x in raw) if r]
    print(f"  {len(raw)} records fetched → {len(rows)} valid rows")

    if not rows:
        print("Nothing to upsert.")
        return

    with httpx.Client() as client:
        upsert(client, rows)

    print(f"  Upserted {len(rows)} rows into Supabase.")


if __name__ == "__main__":
    main()
