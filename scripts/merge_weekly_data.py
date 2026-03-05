#!/usr/bin/env python3
"""
Replace existing alerts_history.json with new historical monthly data
Removes duplicates within the new data based on (alertDate, title, data, category)
"""

import json
from pathlib import Path
from datetime import datetime, timezone

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
    """Create unique key for deduplication."""
    return (
        alert.get('alertDate', ''),
        alert.get('title', ''),
        alert.get('data', ''),
        alert.get('category', 0)
    )

def main():
    print("🔄 Replacing existing data with new historical data...")
    print("=" * 60)
    
    # Check existing data (for stats only)
    existing_count = 0
    if EXISTING_FILE.exists():
        existing_data = json.loads(EXISTING_FILE.read_text(encoding='utf-8'))
        existing_count = len(existing_data)
        print(f"📂 Found {existing_count} existing records (will be replaced)")
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
    
    # Deduplicate new data only
    seen = set()
    final_data = []
    
    for record in monthly_data:
        key = create_key(record)
        if key not in seen:
            seen.add(key)
            final_data.append(record)
    
    # Sort by alertDate (most recent first)
    final_data.sort(key=lambda x: x.get('alertDate', ''), reverse=True)
    
    print(f"\n📊 Statistics:")
    print(f"   Old records (replaced): {existing_count}")
    print(f"   New records collected: {len(monthly_data)}")
    print(f"   New unique records: {len(final_data)}")
    print(f"   Duplicates removed: {len(monthly_data) - len(final_data)}")
    
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
        "replaced_records": existing_count
    }
    METADATA_FILE.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    print(f"\n✅ Replaced data in {OUTPUT_FILE}")
    print(f"📈 Total records: {len(final_data)}")
    print(f"🕒 Updated metadata at: {metadata['updated_at_utc']}")

if __name__ == '__main__':
    main()
