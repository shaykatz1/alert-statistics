#!/usr/bin/env python3
"""
משוך התרעות מערים חסרות ומוסיף אותן לנתונים הקיימים
"""

import requests
import json
from urllib.parse import quote
from pathlib import Path

def fetch_alerts_by_city(city_name, mode=3):
    """Fetch alerts for a specific city"""
    city_encoded = quote(city_name)
    url = f"https://alerts-history.oref.org.il//Shared/Ajax/GetAlarmsHistory.aspx?lang=he&mode={mode}&city_0={city_encoded}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"✓ {city_name}: {len(data)} alerts")
        return data
    except Exception as e:
        print(f"✗ {city_name}: Error - {e}")
        return []

def main():
    print("=" * 60)
    print("משוך ערים חסרות")
    print("=" * 60)
    
    # ערים חסרות שצריך למשוך
    missing_cities = [
        "תל אביב - דרום העיר ויפו"
    ]
    
    # טען נתונים קיימים
    monthly_file = Path("data/historical_monthly.json")
    if monthly_file.exists():
        existing_data = json.loads(monthly_file.read_text(encoding='utf-8'))
        print(f"\n📂 נתונים קיימים: {len(existing_data)} רשומות")
    else:
        existing_data = []
        print("\n📂 אין נתונים קיימים")
    
    # משוך ערים חסרות
    new_alerts = []
    existing_rids = set(alert['rid'] for alert in existing_data)
    
    for city in missing_cities:
        print(f"\nמושך: {city}...")
        alerts = fetch_alerts_by_city(city, mode=3)
        
        # הוסף רק התרעות חדשות (לפי rid)
        for alert in alerts:
            if alert['rid'] not in existing_rids:
                new_alerts.append(alert)
                existing_rids.add(alert['rid'])
    
    # מזג נתונים
    merged_data = existing_data + new_alerts
    merged_data.sort(key=lambda x: x['alertDate'], reverse=True)
    
    print(f"\n{'='*60}")
    print(f"📊 סטטיסטיקה:")
    print(f"   נתונים קיימים: {len(existing_data)}")
    print(f"   רשומות חדשות: {len(new_alerts)}")
    print(f"   סה\"כ אחרי מיזוג: {len(merged_data)}")
    print(f"{'='*60}")
    
    # שמור
    monthly_file.write_text(
        json.dumps(merged_data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    print(f"\n✅ עודכן: {monthly_file}")
    print("\n📌 עכשיו הרץ:")
    print("   python3 scripts/merge_weekly_data.py")

if __name__ == '__main__':
    main()
