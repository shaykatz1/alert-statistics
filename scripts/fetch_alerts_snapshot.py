from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json"
OUT = Path("docs/data/alerts_history.json")
META = Path("docs/data/metadata.json")


def main() -> None:
    # Add User-Agent to avoid being blocked
    res = subprocess.run(
        ["curl", "-s", "--max-time", "30", "-A", "Mozilla/5.0", URL],
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
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response from API", file=sys.stderr)
        print(f"Response preview: {payload[:200]}", file=sys.stderr)
        print(f"JSON Error: {e}", file=sys.stderr)
        raise SystemExit(1)
    
    # Ensure we got a list
    if not isinstance(data, list):
        print(f"Error: Expected list, got {type(data).__name__}", file=sys.stderr)
        raise SystemExit(1)
    
    # Write the data
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    META.write_text(
        json.dumps({"source": URL, "updated_at_utc": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )
    
    print(f"Successfully fetched {len(data)} alert records")


if __name__ == "__main__":
    main()
