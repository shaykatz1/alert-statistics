#!/usr/bin/env python3
"""
Merge existing alerts_history.json with new historical monthly data
Removes duplicates based on (alertDate, title, data, category)
Preserves old content that doesn't exist in the new historical fetch
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

EXISTING_FILE = Path("docs/data/alerts_history.json")
MONTHLY_FILE = Path("data/historical_monthly.json")
OUTPUT_FILE = Path("docs/data/alerts_history.json")
METADATA_FILE = Path("docs/data/metadata.json")

def normalize_alert(alert):
    """
    Convert weekly format to existing format and create dedup key.
    Weekly format: {data, date, time, alertDate, category, category_desc, matrix_id, rid}
    Existing format: {alertDate, title, data, category}
    """
    # Map category_desc to title
    title = alert.get('category_desc', '')
    if title.endswith(' - האירוע הסתיים'):
        title = title.replace(' - האירוע הסתיים', ' - האירוע הסתיים')
    elif title.endswith(' -  האירוע הסתיים'):
        title = title.replace(' -  האירוע הסתיים', ' - האירוע הסתיים')
    
    return {
        'alertDate': alert.get('alertDate', ''),
        'title': title,
        'data': alert.get('data', ''),
        'category': alert.get('category', 0)
    }

def create_key(alert):
    """Create unique key for exact deduplication."""
    return (
        alert.get('alertDate', ''),
        alert.get('title', ''),
        alert.get('data', ''),
        alert.get('category', 0)
    )

def create_group_key(alert):
    """Create group key for time-based deduplication (without timestamp)."""
    return (
        alert.get('title', ''),
        alert.get('data', ''),
        alert.get('category', 0)
    )

def remove_time_duplicates(alerts, time_threshold_minutes=2):
    """
    Remove alerts that are within time_threshold_minutes of each other
    for the same location/title/category combination.
    Keeps the earliest occurrence.
    """
    from collections import defaultdict
    
    # Group alerts by (title, data, category)
    groups = defaultdict(list)
    for alert in alerts:
        key = create_group_key(alert)
        groups[key].append(alert)
    
    # Within each group, remove time duplicates
    deduplicated = []
    duplicates_removed = 0
    
    for key, group_alerts in groups.items():
        # Sort by alertDate
        sorted_alerts = sorted(group_alerts, key=lambda x: x.get('alertDate', ''))
        
        # Keep first alert in each time window
        kept_alerts = []
        for alert in sorted_alerts:
            should_keep = True
            alert_time = None
            
            try:
                alert_time = datetime.fromisoformat(alert['alertDate'].replace('Z', '+00:00'))
            except:
                # If we can't parse the time, keep the alert
                kept_alerts.append(alert)
                continue
            
            # Check if this alert is too close to any kept alert
            for kept_alert in kept_alerts:
                try:
                    kept_time = datetime.fromisoformat(kept_alert['alertDate'].replace('Z', '+00:00'))
                    diff_minutes = abs((alert_time - kept_time).total_seconds() / 60)
                    
                    if diff_minutes <= time_threshold_minutes:
                        should_keep = False
                        duplicates_removed += 1
                        break
                except:
                    pass
            
            if should_keep:
                kept_alerts.append(alert)
        
        deduplicated.extend(kept_alerts)
    
    return deduplicated, duplicates_removed

def main():
    print("🔄 Merging existing data with new historical data...")
    print("=" * 60)
    
    # Load existing data
    existing_data = []
    existing_count = 0
    if EXISTING_FILE.exists():
        existing_data = json.loads(EXISTING_FILE.read_text(encoding='utf-8'))
        existing_count = len(existing_data)
        print(f"📂 Found {existing_count} existing records")
    else:
        print("📂 No existing data found")
    
    # Load monthly data
    if not MONTHLY_FILE.exists():
        print(f"❌ Monthly data file not found: {MONTHLY_FILE}")
        return
    
    monthly_data_raw = json.loads(MONTHLY_FILE.read_text(encoding='utf-8'))
    print(f"📥 Loaded {len(monthly_data_raw)} monthly records")
    
    # Normalize monthly data to existing format
    monthly_data = [normalize_alert(alert) for alert in monthly_data_raw]
    
    # Merge existing and new data, removing exact duplicates
    seen = set()
    merged_data = []
    
    # Process both existing and new data together
    all_records = existing_data + monthly_data
    
    for record in all_records:
        key = create_key(record)
        if key not in seen:
            seen.add(key)
            merged_data.append(record)
    
    exact_duplicates = len(all_records) - len(merged_data)
    print(f"\n📊 Phase 1 - Exact deduplication:")
    print(f"   Total records before: {len(all_records)}")
    print(f"   Exact duplicates removed: {exact_duplicates}")
    print(f"   Records after exact dedup: {len(merged_data)}")
    
    # Remove time-based duplicates (alerts within 2 minutes)
    print(f"\n📊 Phase 2 - Time-based deduplication (within 2 minutes)...")
    final_data, time_duplicates = remove_time_duplicates(merged_data, time_threshold_minutes=2)
    
    # Sort by alertDate (most recent first)
    final_data.sort(key=lambda x: x.get('alertDate', ''), reverse=True)
    
    total_duplicates = exact_duplicates + time_duplicates
    new_records_added = len(final_data) - existing_count
    
    print(f"   Time duplicates removed: {time_duplicates}")
    
    print(f"\n📊 Final Statistics:")
    print(f"   Old records: {existing_count}")
    print(f"   New records collected: {len(monthly_data)}")
    print(f"   Total after merge: {len(final_data)}")
    print(f"   Total duplicates removed: {total_duplicates}")
    print(f"   Net new records added: {new_records_added}")
    
    # Save new data (replacing old)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(final_data, ensure_ascii=False, indent=0),
        encoding='utf-8'
    )
    
    # Update metadata
    metadata = {
        "source": "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_records": len(final_data),
        "previous_records": existing_count,
        "new_records_added": new_records_added
    }
    METADATA_FILE.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    print(f"\n✅ Merged data saved to {OUTPUT_FILE}")
    print(f"📈 Total records: {len(final_data)}")
    print(f"🕒 Updated metadata at: {metadata['updated_at_utc']}")

if __name__ == '__main__':
    main()
