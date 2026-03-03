from __future__ import annotations

import io
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

HISTORY_URL = "https://www.oref.org.il/WarningMessages/alert/History/AlertsHistory.json"
SETTLEMENT_REGION_PATH = Path("data/settlement_regions.csv")

MISSILE_CATEGORY = 1
MISSILE_CATEGORY_END = 13
ADVANCE_WARNING_CATEGORY = 14
MISSILE_TITLE = "ירי רקטות וטילים"


@st.cache_data(ttl=60)
def fetch_alerts_history() -> pd.DataFrame:
    """Fetch alert history from Home Front Command using curl for TLS compatibility."""
    result = subprocess.run(
        ["curl", "-s", "--max-time", "20", HISTORY_URL],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("שגיאה במשיכת נתונים מפיקוד העורף")

    payload = result.stdout.lstrip("\ufeff").strip()
    if not payload:
        raise RuntimeError("התקבלה תגובה ריקה מפיקוד העורף")

    try:
        rows = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("לא ניתן לפענח את תשובת פיקוד העורף") from exc

    df = pd.DataFrame(rows)
    required_columns = {"alertDate", "title", "data", "category"}
    missing = required_columns - set(df.columns)
    if missing:
        raise RuntimeError(f"חסרים שדות בתשובה: {', '.join(sorted(missing))}")

    df = df.rename(columns={"data": "settlement"})
    df["alert_dt"] = pd.to_datetime(df["alertDate"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["alert_dt"])

    # Keep missile launch alerts (category 1), advance warnings (category 14), and event-ended alerts (category 13).
    df = df[
        (df["category"] == MISSILE_CATEGORY) | 
        (df["category"] == MISSILE_CATEGORY_END) |
        (df["category"] == ADVANCE_WARNING_CATEGORY) |
        (df["title"].str.contains(MISSILE_TITLE, na=False))
    ].copy()

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    df = df[(df["alert_dt"] >= week_ago) & (df["alert_dt"] <= now)].copy()

    df["date"] = df["alert_dt"].dt.date
    df["hour"] = df["alert_dt"].dt.hour
    df["day_name"] = df["alert_dt"].dt.day_name()

    df = enrich_with_regions(df)
    return df.sort_values("alert_dt", ascending=False)


def enrich_with_regions(df: pd.DataFrame) -> pd.DataFrame:
    """Attach settlement-to-region mapping if available."""
    if not SETTLEMENT_REGION_PATH.exists():
        df["region"] = "לא ממופה"
        return df

    mapping = pd.read_csv(SETTLEMENT_REGION_PATH)
    expected = {"settlement", "region"}
    missing = expected - set(mapping.columns)
    if missing:
        raise RuntimeError(
            f"בקובץ {SETTLEMENT_REGION_PATH} חייבים להיות עמודות: settlement, region"
        )

    mapping = mapping.dropna(subset=["settlement", "region"]).copy()
    mapping["settlement"] = mapping["settlement"].astype(str).str.strip()
    mapping["region"] = mapping["region"].astype(str).str.strip()

    merged = df.merge(mapping.drop_duplicates("settlement"), how="left", on="settlement")
    merged["region"] = merged["region"].fillna("לא ממופה")
    return merged


def calculate_alert_durations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate time between advance warning (category 14) and first launch in that shelter period.
    
    Logic:
    - Category 14 (advance warning) = shelter entry
    - Category 1 (launches) between 14 and 13 = part of same event
    - Category 13 (all clear) = shelter exit
    - Only the FIRST launch in each 14->13 window is counted
    - Launches outside 14->13 windows AND with 10+ min gap from previous launch = launches without advance warning
    
    Returns a dataframe with durations for each shelter period that had launches.
    """
    from collections import defaultdict
    
    # Group events by settlement
    by_settlement = defaultdict(list)
    for _, row in df.iterrows():
        by_settlement[row["settlement"]].append({
            "alert_dt": row["alert_dt"],
            "category": row["category"]
        })
    
    durations = []
    launches_without_warning_count = 0
    total_launches = 0
    
    # For each settlement, find shelter windows (14->13) and first launch in each
    for settlement, events in by_settlement.items():
        # Sort by time
        sorted_events = sorted(events, key=lambda x: x["alert_dt"])
        
        in_shelter = False
        shelter_start = None
        first_launch_in_window = None
        last_launch_time = None
        
        for event in sorted_events:
            cat = event["category"]
            
            if cat == ADVANCE_WARNING_CATEGORY and not in_shelter:
                # Start of shelter window
                in_shelter = True
                shelter_start = event["alert_dt"]
                first_launch_in_window = None
                
            elif cat == MISSILE_CATEGORY:
                total_launches += 1
                current_launch_time = event["alert_dt"]
                
                if in_shelter:
                    if first_launch_in_window is None:
                        # First launch in this shelter window
                        first_launch_in_window = current_launch_time
                        duration = (first_launch_in_window - shelter_start).total_seconds()
                        
                        # Only include reasonable durations (1 minute to 30 minutes)
                        if 60 <= duration <= 1800:
                            durations.append({
                                "settlement": settlement,
                                "warning_time": shelter_start,
                                "launch_time": first_launch_in_window,
                                "duration_seconds": duration
                            })
                        last_launch_time = current_launch_time
                else:
                    # Launch without advance warning (outside shelter window)
                    # Only count if 10+ minutes passed since last launch (new event)
                    if last_launch_time is None:
                        launches_without_warning_count += 1
                        last_launch_time = current_launch_time
                    else:
                        time_since_last = (current_launch_time - last_launch_time).total_seconds()
                        if time_since_last >= 600:  # 10 minutes
                            launches_without_warning_count += 1
                        last_launch_time = current_launch_time
                    
            elif cat == MISSILE_CATEGORY_END and in_shelter:
                # End of shelter window
                in_shelter = False
                shelter_start = None
                first_launch_in_window = None
    
    result_df = pd.DataFrame(durations)
    # Store metadata for display
    if not result_df.empty:
        result_df.attrs['launches_without_warning'] = launches_without_warning_count
        result_df.attrs['total_launches'] = total_launches
    
    return result_df


def filter_frame(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("סינונים")

    regions = sorted(df["region"].dropna().unique().tolist())
    settlements = sorted(df["settlement"].dropna().unique().tolist())

    selected_regions = st.sidebar.multiselect("איזורים", regions, default=regions)
    selected_settlements = st.sidebar.multiselect("יישובים", settlements)

    min_hour = int(df["hour"].min()) if not df.empty else 0
    max_hour = int(df["hour"].max()) if not df.empty else 23
    hour_range = st.sidebar.slider("טווח שעות", 0, 23, (min_hour, max_hour))

    filtered = df[df["region"].isin(selected_regions)]
    if selected_settlements:
        filtered = filtered[filtered["settlement"].isin(selected_settlements)]
    filtered = filtered[filtered["hour"].between(hour_range[0], hour_range[1])]

    return filtered


def draw_charts(df: pd.DataFrame) -> None:
    by_settlement = (
        df.groupby("settlement", as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .head(20)
        .rename(columns={"size": "count"})
    )
    by_region = (
        df.groupby("region", as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .rename(columns={"size": "count"})
    )
    by_hour = (
        df.groupby("hour", as_index=False)
        .size()
        .sort_values("hour")
        .rename(columns={"size": "count"})
    )

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(by_settlement, x="count", y="settlement", orientation="h", title="Top 20 יישובים")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.bar(by_region, x="region", y="count", title="שיגורים לפי אזור")
        st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(by_hour, x="hour", y="count", title="שיגורים לפי שעה")
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="ניתוח שיגורים - פיקוד העורף", layout="wide")
    st.title("ניתוח שיגורים מהשבוע האחרון")
    st.caption("מקור נתונים: פיקוד העורף - AlertsHistory.json")

    st.info(
        "האפליקציה מציגה התרעות שיגורים (category=1 / 'ירי רקטות וטילים') מה-7 ימים האחרונים. "
        "לניתוח לפי אזור, הוסף קובץ data/settlement_regions.csv עם עמודות settlement,region."
    )

    if st.button("רענון נתונים"):
        st.cache_data.clear()

    try:
        df = fetch_alerts_history()
    except Exception as exc:
        st.error(str(exc))
        return

    if df.empty:
        st.warning("לא נמצאו התרעות שיגורים בשבוע האחרון.")
        return

    filtered = filter_frame(df)

    if filtered.empty:
        st.warning("אין נתונים אחרי הסינון.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("סה״כ התרעות", f"{len(filtered):,}")
    c2.metric("יישובים ייחודיים", f"{filtered['settlement'].nunique():,}")
    peak_hour = filtered.groupby("hour").size().sort_values(ascending=False).index[0]
    c3.metric("שעת שיא", f"{int(peak_hour):02d}:00")

    # Calculate alert durations
    durations_df = calculate_alert_durations(df)
    
    if not durations_df.empty:
        st.subheader("⏰ ניתוח זמני התרעה מקדימה")
        st.caption("זמן בין התרעה מקדימה (קטגוריה 14 - כניסה למקלט) לשיגור הראשון באותו אירוע")
        
        avg_duration = durations_df["duration_seconds"].mean()
        min_duration = durations_df["duration_seconds"].min()
        max_duration = durations_df["duration_seconds"].max()
        
        # Get metadata
        launches_without_warning = durations_df.attrs.get('launches_without_warning', 0)
        total_launches = durations_df.attrs.get('total_launches', 0)
        launches_with_warning = len(durations_df)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("אירועי התרעה מקדימה", f"{launches_with_warning:,}")
        col2.metric("שיגורים ללא התרעה מקדימה", f"{launches_without_warning:,}")
        col3.metric("זמן ממוצע להתרעה", f"{avg_duration/60:.1f} דקות")
        col4.metric("טווח זמנים", f"{min_duration/60:.0f}-{max_duration/60:.0f} דקות")
        
        # Detailed explanation
        coverage_pct = (launches_with_warning / total_launches * 100) if total_launches > 0 else 0
        st.info(
            f"📊 **ממצאים**: מתוך {total_launches:,} שיגורים סה\"כ, "
            f"{launches_with_warning:,} ({coverage_pct:.1f}%) היו באירועי התרעה מקדימה ו-"
            f"{launches_without_warning:,} ({100-coverage_pct:.1f}%) היו ללא התרעה מקדימה. "
            f"הזמן הממוצע מההתרעה המקדימה לשיגור הראשון הוא **{avg_duration/60:.1f} דקות** "
            f"(טווח: {min_duration/60:.0f}-{max_duration/60:.0f} דקות)."
        )

    draw_charts(filtered)

    st.subheader("טבלת נתונים")
    table_df = filtered[["alert_dt", "settlement", "region", "title", "category"]].copy()
    table_df = table_df.rename(
        columns={
            "alert_dt": "תאריך ושעה",
            "settlement": "יישוב",
            "region": "אזור",
            "title": "סוג התרעה",
            "category": "קטגוריה",
        }
    )
    st.dataframe(table_df, use_container_width=True)

    csv_buffer = io.StringIO()
    table_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="הורדת CSV",
        data=csv_buffer.getvalue().encode("utf-8-sig"),
        file_name="oref_launches_last_7_days.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
