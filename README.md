# Home Front Command Alert Analysis

Tool for analyzing and visualizing alerts from Israel's Home Front Command for the past week.

## What's Included?

The project includes 3 versions of the same tool:

1. **Static Site** (docs/) - For publishing on GitHub Pages
2. **Streamlit App** (app.py) - Fast interactive interface
3. **Flask Server** (server.py) - Full API with web interface

All versions display the same data with similar capabilities:
- Alert analysis: missile launches, shelter entry/exit, aircraft intrusion
- Filtering by date range, hours, and settlements
- Calculation of time spent in shelter
- Hourly charts and settlement comparisons
- CSV export

## How to Run?

### Static Site (recommended for quick viewing)
```bash
cd docs
python3 -m http.server 8000
```
Open browser: `http://localhost:8000`

**Update data:**
```bash
python3 scripts/fetch_alerts_snapshot.py
```

### Streamlit App
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Flask Server
```bash
pip install -r requirements.txt
python server.py
```
Open browser: `http://localhost:8000`

## How Does It Work?

**Data Source:** `https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json`

**Data Updates:**
- **Static Site** - Works with local snapshot, must be updated manually or configure GitHub Actions to update every 2 hours
- **Streamlit + Flask** - Pull data live from Home Front Command (60 second cache)

**Event Counting:** Events that appear in the same second with the same title across multiple settlements are counted only once.

## Updating Data

### Regular Updates (Last 7 Days)

To update the static site with the latest alerts from the past week:

```bash
python3 scripts/fetch_alerts_snapshot.py
```

This fetches data from the Home Front Command API and updates `docs/data/alerts_history.json`.

**Automate with cron:**
```bash
# Edit crontab
crontab -e

# Add this line to update every 2 hours
0 */2 * * * cd /path/to/ && python3 scripts/fetch_alerts_snapshot.py
```

### Historical Data (Older Alerts)

To fetch historical data beyond the last 7 days, you can use the historical fetch script:

```bash
python3 scripts/fetch_historical_correct.py
```

This script uses the Home Front Command's historical API endpoint to fetch older alerts. Note that historical data availability depends on the API's retention period.

**For specific date ranges:**

Edit the script parameters before running to specify:
- Start date
- End date
- Settlement regions (optional)

The historical data will be saved to `data/` directory and can be merged with current data using:

```bash
python3 scripts/merge_weekly_data.py
```
