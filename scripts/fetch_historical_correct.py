#!/usr/bin/env python3
"""
Fetch historical alerts using the correct parameters discovered from manual form submission
Uses mode=3 (last month) with city_0 parameter
"""

import requests
import json
from urllib.parse import quote
from datetime import datetime

def fetch_alerts_by_city(city_name, mode=3):
    """
    Fetch alerts for a specific city
    
    Args:
        city_name: Full city name as it appears in the dropdown (Hebrew)
        mode: 1=last day, 2=last week, 3=last month
    
    Returns:
        List of alert records
    """
    # URL encode the city name
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
        
        if data:
            first_date = data[0]['alertDate']
            last_date = data[-1]['alertDate']
            print(f"  Range: {last_date} → {first_date}")
        
        return data
        
    except Exception as e:
        print(f"✗ {city_name}: Error - {e}")
        return []

def fetch_all_cities_historical(mode=2):
    """
    Fetch historical data for all cities
    """
    print(f"🔍 Fetching cities list...")
    
    # Get list of cities - using GetCitiesMix for the complete accurate list
    cities_url = "https://alerts-history.oref.org.il/Shared/Ajax/GetCitiesMix.aspx?lang=he"
    response = requests.get(cities_url)
    cities = response.json()
    
    print(f"📋 Found {len(cities)} cities")
    print(f"🕐 Mode {mode}: {'Last day' if mode == 1 else 'Last week' if mode == 2 else 'Last month'}")
    print()
    
    all_alerts = []
    unique_rids = set()
    
    for i, city in enumerate(cities, 1):
        city_name = city['label']
        
        # Fetch alerts for this city
        alerts = fetch_alerts_by_city(city_name, mode=mode)
        
        # Deduplicate by rid
        for alert in alerts:
            rid = alert['rid']
            if rid not in unique_rids:
                unique_rids.add(rid)
                all_alerts.append(alert)
        
        if (i % 50) == 0:
            print(f"\n📊 Progress: {i}/{len(cities)} cities - {len(all_alerts)} unique alerts\n")
    
    print(f"\n{'='*80}")
    print(f"✅ DONE!")
    print(f"{'='*80}")
    print(f"Cities processed: {len(cities)}")
    print(f"Total unique alerts: {len(all_alerts)}")
    
    if all_alerts:
        all_alerts.sort(key=lambda x: x['alertDate'], reverse=True)
        print(f"Date range: {all_alerts[-1]['alertDate']} → {all_alerts[0]['alertDate']}")
    
    return all_alerts

def save_historical_data(alerts, filename='data/historical_monthly.json'):
    """Save alerts to file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to {filename}")
    print(f"File size: {len(json.dumps(alerts)) / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    print("\n" + "="*80)
    print("📡 Fetching Historical Alerts Data")
    print("="*80 + "\n")
    
    # Fetch last month's data (mode=3)
    alerts = fetch_all_cities_historical(mode=3)
    
    # Save to file
    if alerts:
        save_historical_data(alerts)
        
        print("\n✅ Ready to merge with existing data!")
        print("   Run: python3 scripts/merge_weekly_data.py")
    else:
        print("\n❌ No data fetched")
