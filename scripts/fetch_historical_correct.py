#!/usr/bin/env python3
"""
Fetch historical alerts using the correct parameters discovered from manual form submission
Uses mode=3 (last month) with city_0 parameter
Includes retry mechanism for failed cities
"""

import requests
import json
import time
import os
from urllib.parse import quote
from datetime import datetime

def fetch_alerts_by_city(city_name, mode=3):
    """
    Fetch alerts for a specific city
    
    Args:
        city_name: Full city name as it appears in the dropdown (Hebrew)
        mode: 1=last day, 2=last week, 3=last month
    
    Returns:
        Tuple of (success: bool, data: list)
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
        
        return (True, data)
        
    except Exception as e:
        print(f"✗ {city_name}: Error - {e}")
        return (False, [])

def fetch_all_cities_historical(mode=3, max_retries=3):
    """
    Fetch historical data for all cities with retry mechanism
    
    Args:
        mode: 1=last day, 2=last week, 3=last month
        max_retries: Number of retry attempts for failed cities
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
    failed_cities = []
    
    # First pass - fetch all cities
    for i, city in enumerate(cities, 1):
        city_name = city['label']
        
        # Fetch alerts for this city
        success, alerts = fetch_alerts_by_city(city_name, mode=mode)
        
        if not success:
            failed_cities.append(city_name)
        else:
            # Deduplicate by rid
            for alert in alerts:
                rid = alert['rid']
                if rid not in unique_rids:
                    unique_rids.add(rid)
                    all_alerts.append(alert)
        
        if (i % 50) == 0:
            print(f"\n📊 Progress: {i}/{len(cities)} cities - {len(all_alerts)} unique alerts - {len(failed_cities)} failed\n")
    
    # Retry failed cities
    if failed_cities:
        print(f"\n{'='*80}")
        print(f"🔄 Retrying {len(failed_cities)} failed cities (up to {max_retries} attempts)...")
        print(f"{'='*80}\n")
        
        for retry_num in range(max_retries):
            if not failed_cities:
                break
                
            print(f"\n🔁 Retry attempt {retry_num + 1}/{max_retries} for {len(failed_cities)} cities:\n")
            
            still_failed = []
            for city_name in failed_cities:
                time.sleep(1)  # Wait 1 second between retries
                success, alerts = fetch_alerts_by_city(city_name, mode=mode)
                
                if not success:
                    still_failed.append(city_name)
                else:
                    # Deduplicate by rid
                    for alert in alerts:
                        rid = alert['rid']
                        if rid not in unique_rids:
                            unique_rids.add(rid)
                            all_alerts.append(alert)
            
            failed_cities = still_failed
            
            if failed_cities:
                print(f"\n   Still failing: {len(failed_cities)} cities")
            else:
                print(f"\n   ✅ All cities fetched successfully!")
    
    print(f"\n{'='*80}")
    print(f"✅ DONE!")
    print(f"{'='*80}")
    print(f"Cities processed: {len(cities)}")
    print(f"Total unique alerts: {len(all_alerts)}")
    
    if failed_cities:
        print(f"\n⚠️  WARNING: {len(failed_cities)} cities still failed after {max_retries} retries:")
        for city in failed_cities:
            print(f"   - {city}")
        print(f"\n💡 You can run the script again or use scripts/fetch_missing_cities.py")
    
    if all_alerts:
        all_alerts.sort(key=lambda x: x['alertDate'], reverse=True)
        print(f"\nDate range: {all_alerts[-1]['alertDate']} → {all_alerts[0]['alertDate']}")
    
    return all_alerts

def save_historical_data(alerts, filename='data/historical_monthly.json'):
    """Save alerts to file"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved to {filename}")
    print(f"File size: {len(json.dumps(alerts)) / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    print("\n" + "="*80)
    print("📡 Fetching Historical Alerts Data")
    print("="*80 + "\n")
    
    # Fetch last month's data (mode=3) with 3 retry attempts
    alerts = fetch_all_cities_historical(mode=3, max_retries=3)
    
    # Save to file
    if alerts:
        save_historical_data(alerts)
        
        print("\n✅ Ready to merge with existing data!")
        print("   Run: python3 scripts/merge_weekly_data.py")
    else:
        print("\n❌ No data fetched")
