#!/usr/bin/env python3
"""
One-time script to merge all historical alert data from previous git commits
into the current alerts_history.json file, removing duplicates.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Paths
ALERTS_FILE = Path("docs/data/alerts_history.json")
META_FILE = Path("docs/data/metadata.json")


def get_file_from_commit(commit_hash: str, file_path: str) -> list | None:
    """Get the content of a file from a specific git commit."""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{file_path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, Exception) as e:
        print(f"  ⚠️  Could not parse data from {commit_hash[:7]}: {e}")
    return None


def get_commits_with_file(file_path: str) -> list[str]:
    """Get all commits that modified the specified file."""
    result = subprocess.run(
        ["git", "log", "--all", "--format=%H", "--", file_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return []


def main() -> None:
    print("🔍 Searching for historical commits...")
    
    # Get all commits that modified the alerts file
    commits = get_commits_with_file(str(ALERTS_FILE))
    
    if not commits:
        print("❌ No commits found with alerts data")
        sys.exit(1)
    
    print(f"📚 Found {len(commits)} commits with alert data\n")
    
    # Collect all unique records
    seen = set()
    all_records = []
    total_from_commits = 0
    
    print("📥 Loading data from commits...")
    for i, commit in enumerate(commits, 1):
        commit_short = commit[:7]
        data = get_file_from_commit(commit, str(ALERTS_FILE))
        
        if data:
            print(f"  [{i}/{len(commits)}] {commit_short}: {len(data)} records")
            total_from_commits += len(data)
            
            for record in data:
                # Create unique key from all fields
                key = (
                    record.get("alertDate"),
                    record.get("title"),
                    record.get("data"),
                    record.get("category")
                )
                if key not in seen:
                    seen.add(key)
                    all_records.append(record)
    
    print(f"\n📊 Summary:")
    print(f"  Total records from all commits: {total_from_commits}")
    print(f"  Unique records after deduplication: {len(all_records)}")
    
    # Sort by date (most recent first)
    all_records.sort(key=lambda x: x.get("alertDate", ""), reverse=True)
    
    # Write the merged data
    print(f"\n💾 Writing merged data to {ALERTS_FILE}...")
    ALERTS_FILE.write_text(json.dumps(all_records, ensure_ascii=False, indent=0), encoding="utf-8")
    
    # Update metadata
    from datetime import datetime, timezone
    META_FILE.write_text(
        json.dumps({
            "source": "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_records": len(all_records),
            "merged_from_commits": len(commits),
            "note": "Merged historical data from all git commits"
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    
    print(f"✅ Successfully merged {len(all_records)} unique records!")
    print(f"📁 Data saved to: {ALERTS_FILE}")
    print(f"📁 Metadata saved to: {META_FILE}")


if __name__ == "__main__":
    main()
