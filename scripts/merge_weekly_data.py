#!/usr/bin/env python3
"""
Merge historical monthly data with existing alerts_history.json
Removes duplicates based on (alertDate, title, data, category)
"""

import json
from pathlib import Path

EXISTING_FILE = Path("docs/data/alerts_history.json")
MONTHLY_FILE = Path("data/historical_monthly.json")
OUTPUT_FILE = Path("docs/data/alerts_history.json")

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
    print("🔄 Merging historical data with existing alerts...")
    print("=" * 60)
    
    # Load existing data
    if EXISTING_FILE.exists():
        existing_data = json.loads(EXISTING_FILE.read_text(encoding='utf-8'))
        print(f"📂 Loaded {len(existing_data)} existing records")
    else:
        existing_data = []
        print("📂 No existing data found")
    
    # Load monthly data
    if not MONTHLY_FILE.exists():
        print(f"❌ Monthly data file not found: {MONTHLY_FILE}")
        return
    
    monthly_data_raw = json.loads(MONTHLY_FILE.read_text(encoding='utf-8'))
    print(f"📥 Loaded {len(monthly_data_raw)} monthly records")
    
    # Normalize monthly data to existing format
    monthly_data = [normalize_alert(alert) for alert in monthly_data_raw]
    
    # Merge and deduplicate
    seen = set()
    merged_data = []
    
    for record in existing_data + monthly_data:
        key = create_key(record)
        if key not in seen:
            seen.add(key)
            merged_data.append(record)
    
    # Sort by alertDate (most recent first)
    merged_data.sort(key=lambda x: x.get('alertDate', ''), reverse=True)
    
    print(f"\n📊 Statistics:")
    print(f"   Existing records: {len(existing_data)}")
    print(f"   Monthly records: {len(monthly_data)}")
    print(f"   Merged unique: {len(merged_data)}")
    print(f"   New records added: {len(merged_data) - len(existing_data)}")
    
    # Save merged data
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(merged_data, ensure_ascii=False, indent=0),
        encoding='utf-8'
    )
    
    print(f"\n✅ Saved to {OUTPUT_FILE}")
    print(f"📈 Total unique records: {len(merged_data)}")

if __name__ == '__main__':
    main()
