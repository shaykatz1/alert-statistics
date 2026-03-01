from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json"
OUT = Path("docs/data/alerts_history.json")
META = Path("docs/data/metadata.json")


def main() -> None:
    res = subprocess.run(["curl", "-s", "--max-time", "30", URL], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise SystemExit("failed to fetch alerts")

    payload = res.stdout.lstrip("\ufeff").strip()
    if not payload:
        raise SystemExit("empty payload")

    data = json.loads(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    META.write_text(
        json.dumps({"source": URL, "updated_at_utc": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
