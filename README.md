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
