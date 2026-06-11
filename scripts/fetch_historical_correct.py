#!/usr/bin/env python3
"""
Fetch historical alerts city-by-city from the oref historical API,
upsert into Supabase, and rebuild the Storage snapshot.

Required env vars:
    SUPABASE_URL         https://xxx.supabase.co
    SUPABASE_SERVICE_KEY service_role secret key

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python3 scripts/fetch_historical_correct.py
"""

from __future__ import annotations

import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
import requests

CITIES_URL = "https://alerts-history.oref.org.il/Shared/Ajax/GetCitiesMix.aspx?lang=he"
ALERTS_URL = "https://alerts-history.oref.org.il/Shared/Ajax/GetAlarmsHistory.aspx"

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

LOCAL_CACHE = Path("data/historical_monthly.json")
PAGE_SIZE = 1000
STORAGE_FILE = "alerts_history.json.gz"


# ---------------------------------------------------------------------------
# Fetch from oref
# ---------------------------------------------------------------------------

def fetch_city(city_name: str, mode: int = 3) -> tuple[bool, list]:
    url = f"{ALERTS_URL}?lang=he&mode={mode}&city_0={quote(city_name)}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"  ✓ {city_name}: {len(data)} alerts")
        return True, data
    except Exception as e:
        print(f"  ✗ {city_name}: {e}")
        return False, []


def fetch_all_cities(mode: int = 3, max_retries: int = 3) -> list[dict]:
    print("Fetching city list...")
    cities = requests.get(CITIES_URL).json()
    print(f"  {len(cities)} cities (mode={mode})\n")

    all_alerts: list[dict] = []
    seen_rids: set = set()
    failed: list[str] = []

    for i, city in enumerate(cities, 1):
        ok, alerts = fetch_city(city["label"], mode)
        if not ok:
            failed.append(city["label"])
        else:
            for a in alerts:
                rid = a.get("rid")
                if rid not in seen_rids:
                    seen_rids.add(rid)
                    all_alerts.append(a)
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(cities)} — {len(all_alerts)} unique alerts, {len(failed)} failed")

    for attempt in range(max_retries):
        if not failed:
            break
        print(f"\nRetry {attempt + 1}/{max_retries} for {len(failed)} cities...")
        still_failed = []
        for city_name in failed:
            time.sleep(1)
            ok, alerts = fetch_city(city_name, mode)
            if not ok:
                still_failed.append(city_name)
            else:
                for a in alerts:
                    rid = a.get("rid")
                    if rid not in seen_rids:
                        seen_rids.add(rid)
                        all_alerts.append(a)
        failed = still_failed

    if failed:
        print(f"\nWarning: {len(failed)} cities still failed: {failed}")

    all_alerts.sort(key=lambda x: x.get("alertDate", ""), reverse=True)
    print(f"\nFetched {len(all_alerts)} unique alerts total")
    return all_alerts


# ---------------------------------------------------------------------------
# Normalize to Supabase row format
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

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
    print("  Reading all rows from DB...")
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
    print(f"  Snapshot uploaded.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    alerts_raw = fetch_all_cities(mode=3, max_retries=3)
    if not alerts_raw:
        print("No data fetched — aborting.")
        return

    # Save local cache
    LOCAL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_CACHE.write_text(json.dumps(alerts_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved local cache → {LOCAL_CACHE}")

    rows = [r for r in (to_row(a) for a in alerts_raw) if r]
    print(f"\nUpserting {len(rows)} rows to Supabase...")

    BATCH = 5_000
    with httpx.Client() as client:
        for i in range(0, len(rows), BATCH):
            upsert_batch(client, rows[i: i + BATCH])
            print(f"  {min(i + BATCH, len(rows))}/{len(rows)}")

        print("\nRebuilding snapshot...")
        all_rows = fetch_all_from_db(client)
        upload_snapshot(client, all_rows)

    print(f"\nDone — {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
