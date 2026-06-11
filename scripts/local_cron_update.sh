#!/bin/bash
# Run this locally every 2 hours to fetch from oref.org.il and update Supabase.
# oref blocks cloud IPs so this must run from a home/personal machine.
#
# Setup (one time):
#   chmod +x scripts/local_cron_update.sh
#   crontab -e
#   Add:  0 */2 * * * /path/to/alert-statistics/scripts/local_cron_update.sh >> /tmp/alert-update.log 2>&1

set -e
cd "$(dirname "$0")/.."

export SUPABASE_URL="https://hipcckjswlfzgngiconi.supabase.co"
export SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhpcGNja2pzd2xmemduZ2ljb25pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTE5NTkyMiwiZXhwIjoyMDk2NzcxOTIyfQ.ZQR8plX_xnd4f_OyKAWoIyr37OhftEVV2Me7dyerK7Y"

python3 scripts/fetch_alerts_snapshot.py
