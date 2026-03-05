from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json"
OUT = Path("docs/data/alerts_history.json")
META = Path("docs/data/metadata.json")


def normalize_alert_date(alert):
    """
    Normalize alertDate by zeroing out seconds to match historical data format.
    Historical API returns dates like: 2026-03-05T10:30:00
    Live API returns dates like: 2026-03-05 10:30:45 (with space, not T)
    """
    if "alertDate" in alert and alert["alertDate"]:
        try:
            date_str = alert["alertDate"]
            # Handle both formats: "2026-03-05T10:30:45" and "2026-03-05 10:30:45"
            if 'T' in date_str:
                separator = 'T'
            elif ' ' in date_str:
                separator = ' '
            else:
                return alert  # Unknown format, skip
            
            # Split by separator
            parts = date_str.split(separator)
            if len(parts) == 2:
                date_part = parts[0]
                time_part = parts[1]
                # Split time by ':'
                time_components = time_part.split(':')
                if len(time_components) >= 3:
                    # Replace seconds with 00
                    time_components[2] = '00'
                    # Use T as the standard separator in output
                    alert["alertDate"] = f"{date_part}T{':'.join(time_components)}"
        except Exception:
            # If anything fails, keep original
            pass
    return alert


def main() -> None:
    # Load existing data if available
    existing_data = []
    if OUT.exists():
        try:
            existing_data = json.loads(OUT.read_text(encoding="utf-8"))
            print(f"Loaded {len(existing_data)} existing records")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load existing data: {e}", file=sys.stderr)
    
    # Add headers to avoid being blocked by WAF/Cloudflare
    res = subprocess.run(
        [
            "curl", "-s", "--max-time", "30",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "-H", "Accept: application/json, text/plain, */*",
            "-H", "Accept-Language: he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
            "-H", "Referer: https://www.oref.org.il/",
            "-H", "Origin: https://www.oref.org.il",
            URL
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    
    if res.returncode != 0:
        print(f"Error: curl failed with code {res.returncode}", file=sys.stderr)
        print(f"Stderr: {res.stderr}", file=sys.stderr)
        raise SystemExit(1)

    payload = res.stdout.lstrip("\ufeff").strip()
    
    if not payload:
        print("Error: Empty response from API", file=sys.stderr)
        raise SystemExit(1)
    
    # Try to parse JSON with better error handling
    try:
        new_data = json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response from API", file=sys.stderr)
        print(f"Response preview: {payload[:200]}", file=sys.stderr)
        print(f"JSON Error: {e}", file=sys.stderr)
        raise SystemExit(1)
    
    # Ensure we got a list
    if not isinstance(new_data, list):
        print(f"Error: Expected list, got {type(new_data).__name__}", file=sys.stderr)
        raise SystemExit(1)
    
    print(f"Fetched {len(new_data)} new records from API")
    
    # Normalize alert dates by zeroing out seconds to match historical data
    # Need to normalize both existing and new data for proper deduplication
    existing_data = [normalize_alert_date(alert) for alert in existing_data]
    new_data = [normalize_alert_date(alert) for alert in new_data]
    
    # Merge data: create a set of tuples for deduplication
    # We use all fields as the unique key
    seen = set()
    merged_data = []
    
    for record in existing_data + new_data:
        # Create a unique key from all fields
        key = (
            record.get("alertDate"),
            record.get("title"),
            record.get("data"),
            record.get("category")
        )
        if key not in seen:
            seen.add(key)
            merged_data.append(record)
    
    # Sort by alertDate (most recent first)
    merged_data.sort(key=lambda x: x.get("alertDate", ""), reverse=True)
    
    print(f"Total unique records after merge: {len(merged_data)}")
    print(f"New records added: {len(merged_data) - len(existing_data)}")
    
    # Write the merged data
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(merged_data, ensure_ascii=False, indent=0), encoding="utf-8")
    META.write_text(
        json.dumps({
            "source": URL,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_records": len(merged_data),
            "new_records_added": len(merged_data) - len(existing_data)
        }, indent=2),
        encoding="utf-8",
    )
    
    print(f"Successfully updated alerts history")


if __name__ == "__main__":
    main()
