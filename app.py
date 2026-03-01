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

    # Keep missile launch alerts only.
    df = df[(df["category"] == MISSILE_CATEGORY) | (df["title"].str.contains(MISSILE_TITLE, na=False))].copy()

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
