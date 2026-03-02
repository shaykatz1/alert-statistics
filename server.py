from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

LOCAL_HISTORY_FILE = Path(__file__).parent / "docs" / "data" / "alerts_history.json"
MISSILE_CATEGORY = 1
MISSILE_TITLE = "ירי רקטות וטילים"

app = Flask(__name__)

_cached_df: pd.DataFrame | None = None
_cached_at: datetime | None = None
CACHE_SECONDS = 60


def classify_alert(title: str, category: int) -> str:
    title = title or ""

    # Check for event end FIRST (before checking event type)
    if category == 13 or "ניתן לצאת" in title or "האירוע הסתיים" in title or "החשש הוסר" in title:
        return "shelter_exit"

    if category == 14 or "בדקות הקרובות צפויות להתקבל התרעות" in title or "היכנסו" in title or "להיכנס" in title:
        return "shelter_enter"

    if category == MISSILE_CATEGORY or MISSILE_TITLE in title:
        return "launch"

    if category == 2 or "חדירת כלי טיס עוין" in title or "כלי טיס עוין" in title:
        return "aircraft"

    if category == 10 or "חדירת מחבלים" in title:
        return "infiltration"

    return "other"


def fetch_alerts_history() -> pd.DataFrame:
    global _cached_df, _cached_at

    now = datetime.now()
    if _cached_df is not None and _cached_at is not None:
        if (now - _cached_at).total_seconds() < CACHE_SECONDS:
            return _cached_df.copy()

    if not LOCAL_HISTORY_FILE.exists():
        raise RuntimeError(f"Local data file not found: {LOCAL_HISTORY_FILE}")
    
    with open(LOCAL_HISTORY_FILE, 'r', encoding='utf-8') as f:
        rows = json.load(f)
    
    if not rows:
        raise RuntimeError("empty data in local file")

    df = pd.DataFrame(rows)
    needed = {"alertDate", "title", "data", "category"}
    if not needed.issubset(set(df.columns)):
        raise RuntimeError("missing required fields in response")

    df = df.rename(columns={"data": "settlement"})
    df["alert_dt"] = pd.to_datetime(df["alertDate"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["alert_dt"]).copy()

    # Show last 30 days to include all historical data
    month_ago = now - timedelta(days=30)
    df = df[(df["alert_dt"] >= month_ago) & (df["alert_dt"] <= now)].copy()

    df["alert_type"] = df.apply(lambda r: classify_alert(str(r.get("title", "")), int(r.get("category", 0))), axis=1)
    df = df[df["alert_type"].isin(["launch", "shelter_enter", "shelter_exit", "aircraft", "infiltration"])].copy()

    df["hour"] = df["alert_dt"].dt.hour
    df["date"] = df["alert_dt"].dt.strftime("%Y-%m-%d")
    df["datetime"] = df["alert_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["event_key"] = (
        df["datetime"].astype(str) + "|" + df["title"].astype(str) + "|" + df["category"].astype(str)
    )

    df = df.sort_values("alert_dt", ascending=False)
    _cached_df = df.copy()
    _cached_at = now
    return df


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise RuntimeError("invalid date format, expected YYYY-MM-DD")


def apply_base_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, str, datetime | None, datetime | None]:
    mode = request.args.get("mode", default="week", type=str)
    out = df.copy()

    range_start: datetime | None = None
    range_end: datetime | None = None
    now = datetime.now()

    last_days_map = {
        "last_1d": 1,
        "last_2d": 2,
        "last_3d": 3,
        "last_4d": 4,
    }

    if mode in last_days_map:
        days = last_days_map[mode]
        range_start = now - timedelta(days=days)
        range_end = now
        out = out[(out["alert_dt"] >= range_start) & (out["alert_dt"] <= range_end)]
        return out, mode, range_start, range_end

    if mode == "custom":
        start_date = parse_date(request.args.get("start_date", type=str))
        end_date = parse_date(request.args.get("end_date", type=str))

        hour_from = max(0, min(23, request.args.get("hour_from", default=0, type=int)))
        hour_to = max(0, min(23, request.args.get("hour_to", default=23, type=int)))

        if start_date and end_date:
            if end_date < start_date:
                start_date, end_date = end_date, start_date

            date_only = out["alert_dt"].dt.date
            out = out[(date_only >= start_date) & (date_only <= end_date)]
            range_start = datetime.combine(start_date, datetime.min.time()) + timedelta(hours=hour_from)
            range_end = datetime.combine(end_date, datetime.min.time()) + timedelta(hours=hour_to, minutes=59, seconds=59)

        out = out[out["hour"].between(hour_from, hour_to)]

    return out, mode, range_start, range_end


def extract_shelter_stays(df: pd.DataFrame, range_start: datetime | None, range_end: datetime | None) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=["settlement", "start_dt", "end_dt", "duration_minutes"])

    now = datetime.now()
    effective_end = range_end if range_end is not None else now

    data = df[df["alert_type"].isin(["shelter_enter", "shelter_exit"])][
        ["settlement", "alert_dt", "alert_type"]
    ].sort_values(["settlement", "alert_dt"])

    records: list[dict] = []

    for settlement, group in data.groupby("settlement"):
        open_at: datetime | None = None

        for _, row in group.iterrows():
            at = row["alert_dt"]
            typ = row["alert_type"]

            if typ == "shelter_enter":
                if open_at is None:
                    open_at = at
                continue

            if typ == "shelter_exit" and open_at is not None:
                start = open_at
                end = at

                if range_start is not None:
                    start = max(start, range_start)
                if range_end is not None:
                    end = min(end, range_end)

                if end > start:
                    records.append(
                        {
                            "settlement": settlement,
                            "start_dt": start,
                            "end_dt": end,
                            "duration_minutes": (end - start).total_seconds() / 60.0,
                        }
                    )

                open_at = None

        if open_at is not None:
            start = open_at
            end = effective_end
            if range_start is not None:
                start = max(start, range_start)
            if range_end is not None:
                end = min(end, range_end)

            if end > start:
                records.append(
                    {
                        "settlement": settlement,
                        "start_dt": start,
                        "end_dt": end,
                        "duration_minutes": (end - start).total_seconds() / 60.0,
                    }
                )

    return pd.DataFrame(records)


def summarize_shelter_stays(stays_df: pd.DataFrame) -> pd.DataFrame:
    if len(stays_df) == 0:
        return pd.DataFrame(columns=["settlement", "shelter_minutes", "shelter_hours", "stay_count", "avg_stay_minutes"])

    summary = (
        stays_df.groupby("settlement", as_index=False)
        .agg(
            shelter_minutes=("duration_minutes", "sum"),
            stay_count=("duration_minutes", "size"),
        )
    )
    summary["shelter_minutes"] = summary["shelter_minutes"].round().astype(int)
    summary["shelter_hours"] = (summary["shelter_minutes"] / 60.0).round(2)
    summary["avg_stay_minutes"] = (summary["shelter_minutes"] / summary["stay_count"]).round(1)
    return summary


def build_hourly_shelter_minutes(stays_df: pd.DataFrame) -> list[dict]:
    # Minutes spent in shelter bucketed by hour-of-day (0-23), across all matching settlements.
    buckets = [0.0] * 24
    if len(stays_df) == 0:
        return [{"hour": h, "minutes": 0} for h in range(24)]

    for _, row in stays_df.iterrows():
        current = row["start_dt"]
        end = row["end_dt"]
        while current < end:
            next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            segment_end = min(end, next_hour)
            buckets[current.hour] += (segment_end - current).total_seconds() / 60.0
            current = segment_end

    return [{"hour": h, "minutes": int(round(buckets[h]))} for h in range(24)]


def apply_settlement_filters(
    df: pd.DataFrame, shelter_df: pd.DataFrame, stays_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    selected_settlement = request.args.get("settlement", default="", type=str).strip()
    selected_settlements = [selected_settlement] if selected_settlement else []

    min_minutes = request.args.get("min_shelter_minutes", default=0, type=int)
    max_minutes = request.args.get("max_shelter_minutes", default=-1, type=int)

    allowed_by_duration = set(shelter_df["settlement"].tolist())
    if len(shelter_df) > 0:
        duration_filtered = shelter_df[shelter_df["shelter_minutes"] >= max(0, min_minutes)]
        if max_minutes >= 0:
            duration_filtered = duration_filtered[duration_filtered["shelter_minutes"] <= max_minutes]
        allowed_by_duration = set(duration_filtered["settlement"].tolist())

    out = df[df["settlement"].isin(allowed_by_duration)]

    if selected_settlements:
        out = out[out["settlement"].isin(selected_settlements)]

    shelter_out = shelter_df[shelter_df["settlement"].isin(out["settlement"].unique().tolist())].copy()
    stays_out = stays_df[stays_df["settlement"].isin(out["settlement"].unique().tolist())].copy()
    return out, shelter_out, stays_out, selected_settlements


def build_compare_series(df: pd.DataFrame, selected_settlements: list[str]) -> tuple[list[str], list[dict]]:
    launch_df = df[df["alert_type"] == "launch"]
    if len(launch_df) == 0:
        return [], []

    if selected_settlements:
        compare_settlements = [s for s in selected_settlements if s in set(launch_df["settlement"])]
    else:
        compare_settlements = (
            launch_df.groupby("settlement").size().sort_values(ascending=False).head(5).index.tolist()
        )

    compare_df = launch_df[launch_df["settlement"].isin(compare_settlements)]
    by_day_settlement = (
        compare_df.groupby(["date", "settlement"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["date", "settlement"])
        .to_dict(orient="records")
    )
    return compare_settlements, by_day_settlement


def build_compare_two_settlements(df: pd.DataFrame, settlement_a: str, settlement_b: str) -> list[dict]:
    if not settlement_a or not settlement_b:
        return []

    launch_df = df[df["alert_type"] == "launch"]
    compare_df = launch_df[launch_df["settlement"].isin([settlement_a, settlement_b])]
    if len(compare_df) == 0:
        return []

    return (
        compare_df.groupby(["date", "settlement"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["date", "settlement"])
        .to_dict(orient="records")
    )


def build_hourly_counts(events_df: pd.DataFrame) -> list[dict]:
    counts = events_df.groupby("hour").size().to_dict() if len(events_df) else {}
    return [{"hour": h, "count": int(counts.get(h, 0))} for h in range(24)]


def build_compare_two_totals(
    df: pd.DataFrame, stays_df: pd.DataFrame, settlement_a: str, settlement_b: str
) -> tuple[list[dict], list[dict]]:
    if not settlement_a or not settlement_b:
        return [], []

    launch_subset = df[
        (df["alert_type"] == "launch") & (df["settlement"].isin([settlement_a, settlement_b]))
    ][["settlement", "event_key"]].drop_duplicates()
    launch_counts = launch_subset.groupby("settlement").size().to_dict()
    compare_two_launch_totals = [
        {"settlement": settlement_a, "count": int(launch_counts.get(settlement_a, 0))},
        {"settlement": settlement_b, "count": int(launch_counts.get(settlement_b, 0))},
    ]

    shelter_subset = stays_df[stays_df["settlement"].isin([settlement_a, settlement_b])]
    shelter_minutes = shelter_subset.groupby("settlement")["duration_minutes"].sum().to_dict()
    compare_two_shelter_totals = [
        {"settlement": settlement_a, "minutes": int(round(float(shelter_minutes.get(settlement_a, 0.0))))},
        {"settlement": settlement_b, "minutes": int(round(float(shelter_minutes.get(settlement_b, 0.0))))},
    ]

    return compare_two_launch_totals, compare_two_shelter_totals


def build_compare_two_hourly(
    df: pd.DataFrame, stays_df: pd.DataFrame, settlement_a: str, settlement_b: str
) -> tuple[list[dict], list[dict]]:
    if not settlement_a or not settlement_b:
        return [], []

    settlements = [settlement_a, settlement_b]

    launch_subset = df[
        (df["alert_type"] == "launch") & (df["settlement"].isin(settlements))
    ][["settlement", "event_key", "hour"]].drop_duplicates(["settlement", "event_key"])
    launch_counts = launch_subset.groupby(["settlement", "hour"]).size().to_dict()
    compare_two_hourly_launches = [
        {"settlement": s, "hour": h, "count": int(launch_counts.get((s, h), 0))}
        for s in settlements
        for h in range(24)
    ]

    stays_subset = stays_df[stays_df["settlement"].isin(settlements)]
    shelter_buckets: dict[tuple[str, int], float] = {(s, h): 0.0 for s in settlements for h in range(24)}
    for _, row in stays_subset.iterrows():
        current = row["start_dt"]
        end = row["end_dt"]
        settlement = row["settlement"]
        while current < end:
            next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            segment_end = min(end, next_hour)
            shelter_buckets[(settlement, current.hour)] += (segment_end - current).total_seconds() / 60.0
            current = segment_end

    compare_two_hourly_shelter = [
        {"settlement": s, "hour": h, "minutes": int(round(shelter_buckets.get((s, h), 0.0)))}
        for s in settlements
        for h in range(24)
    ]

    return compare_two_hourly_launches, compare_two_hourly_shelter


def build_unique_events(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=["event_key", "datetime", "title", "category", "alert_type", "settlements", "settlements_count", "hour"])

    events = (
        df.groupby("event_key", as_index=False)
        .agg(
            datetime=("datetime", "first"),
            title=("title", "first"),
            category=("category", "first"),
            alert_type=("alert_type", "first"),
            hour=("hour", "first"),
            settlements_count=("settlement", "nunique"),
            settlements=("settlement", lambda s: ", ".join(sorted(set(s.tolist()))[:15])),
        )
        .sort_values("datetime", ascending=False)
    )
    return events


def get_settlement_stats(
    shelter_df: pd.DataFrame, stays_df: pd.DataFrame, selected_settlement: str | None
) -> dict:
    if not selected_settlement:
        return {
            "settlement": None,
            "total_shelter_minutes": 0,
            "avg_stay_minutes": 0.0,
            "stay_count": 0,
            "longest_stay_minutes": 0,
            "longest_stay_start": None,
            "longest_stay_end": None,
        }

    match = shelter_df[shelter_df["settlement"] == selected_settlement]
    if len(match) == 0:
        return {
            "settlement": selected_settlement,
            "total_shelter_minutes": 0,
            "avg_stay_minutes": 0.0,
            "stay_count": 0,
            "longest_stay_minutes": 0,
            "longest_stay_start": None,
            "longest_stay_end": None,
        }

    row = match.iloc[0]
    settlement_stays = stays_df[stays_df["settlement"] == selected_settlement]
    longest_stay_minutes = 0
    longest_stay_start = None
    longest_stay_end = None
    if len(settlement_stays) > 0:
        max_row = settlement_stays.sort_values("duration_minutes", ascending=False).iloc[0]
        longest_stay_minutes = int(round(float(max_row["duration_minutes"])))
        longest_stay_start = max_row["start_dt"].strftime("%Y-%m-%d %H:%M:%S")
        longest_stay_end = max_row["end_dt"].strftime("%Y-%m-%d %H:%M:%S")

    return {
        "settlement": selected_settlement,
        "total_shelter_minutes": int(row["shelter_minutes"]),
        "avg_stay_minutes": float(row["avg_stay_minutes"]),
        "stay_count": int(row["stay_count"]),
        "longest_stay_minutes": longest_stay_minutes,
        "longest_stay_start": longest_stay_start,
        "longest_stay_end": longest_stay_end,
    }


def build_compare_two_stats(
    shelter_df: pd.DataFrame, stays_df: pd.DataFrame, settlement_a: str, settlement_b: str
) -> dict:
    return {
        "a": get_settlement_stats(shelter_df, stays_df, settlement_a if settlement_a else None),
        "b": get_settlement_stats(shelter_df, stays_df, settlement_b if settlement_b else None),
    }


@app.route("/")
def home() -> str:
    return render_template("index.html")


@app.route("/api/alerts")
def alerts_api():
    try:
        df = fetch_alerts_history()
        base_filtered, mode, range_start, range_end = apply_base_filters(df)

        stays_df = extract_shelter_stays(base_filtered, range_start, range_end)
        shelter_df = summarize_shelter_stays(stays_df)
        filtered, shelter_filtered, stays_filtered, selected_settlements = apply_settlement_filters(
            base_filtered, shelter_df, stays_df
        )

        selected_types = [t for t in request.args.getlist("alert_type") if t in {"launch", "shelter_enter", "shelter_exit", "aircraft", "infiltration"}]
        if selected_types:
            filtered_for_events = filtered[filtered["alert_type"].isin(selected_types)]
        else:
            filtered_for_events = filtered

        unique_events = build_unique_events(filtered_for_events)

        stats_settlement = request.args.get("stats_settlement", default=None, type=str)
        if not stats_settlement and len(selected_settlements) == 1:
            stats_settlement = selected_settlements[0]
        selected_settlement_stats = get_settlement_stats(shelter_filtered, stays_filtered, stats_settlement)

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    launch_events = build_unique_events(filtered[filtered["alert_type"] == "launch"])
    by_hour_launches = build_hourly_counts(launch_events)

    aircraft_events = build_unique_events(filtered[filtered["alert_type"] == "aircraft"])
    by_hour_aircraft = build_hourly_counts(aircraft_events)
    by_hour_shelter_minutes = build_hourly_shelter_minutes(stays_filtered)

    compare_settlements, by_day_settlement = build_compare_series(filtered, selected_settlements)
    compare_a = request.args.get("compare_a", default="", type=str).strip()
    compare_b = request.args.get("compare_b", default="", type=str).strip()
    by_day_two_settlements = build_compare_two_settlements(base_filtered, compare_a, compare_b)
    compare_two_launch_totals, compare_two_shelter_totals = build_compare_two_totals(
        base_filtered, stays_df, compare_a, compare_b
    )
    compare_two_hourly_launches, compare_two_hourly_shelter = build_compare_two_hourly(
        base_filtered, stays_df, compare_a, compare_b
    )
    compare_two_stats = build_compare_two_stats(shelter_df, stays_df, compare_a, compare_b)

    rows = unique_events[["datetime", "title", "category", "alert_type", "settlements_count", "settlements"]].to_dict(orient="records")
    peak_hour = int(pd.DataFrame(by_hour_launches).sort_values("count", ascending=False).iloc[0]["hour"]) if by_hour_launches else None
    counts_by_type = unique_events.groupby("alert_type").size().to_dict()

    all_dates = sorted(df["date"].dropna().unique().tolist())

    payload = {
        "meta": {
            "total_unique_alerts": int(len(unique_events)),
            "total_rows_before_dedup": int(len(filtered_for_events)),
            "unique_settlements": int(filtered["settlement"].nunique()) if len(filtered) else 0,
            "peak_hour": peak_hour,
            "available_settlements": sorted(df["settlement"].dropna().unique().tolist()),
            "available_dates": all_dates,
            "default_start_date": all_dates[0] if all_dates else None,
            "default_end_date": all_dates[-1] if all_dates else None,
            "available_types": ["launch", "shelter_enter", "shelter_exit", "aircraft"],
            "source": str(LOCAL_HISTORY_FILE),
            "window_days": 7,
            "mode": mode,
            "has_shelter_history": bool((df["alert_type"] == "shelter_enter").any() and (df["alert_type"] == "shelter_exit").any()),
            "selected_settlement_stats": selected_settlement_stats,
            "type_counts": {
                "launch": int(counts_by_type.get("launch", 0)),
                "shelter_enter": int(counts_by_type.get("shelter_enter", 0)),
                "shelter_exit": int(counts_by_type.get("shelter_exit", 0)),
                "aircraft": int(counts_by_type.get("aircraft", 0)),
            },
        },
        "groups": {
            "by_hour_launches": by_hour_launches,
            "by_hour_aircraft": by_hour_aircraft,
            "by_hour_shelter_minutes": by_hour_shelter_minutes,
            "compare_settlements": compare_settlements,
            "by_day_settlement": by_day_settlement,
            "by_day_two_settlements": by_day_two_settlements,
            "compare_two_launch_totals": compare_two_launch_totals,
            "compare_two_shelter_totals": compare_two_shelter_totals,
            "compare_two_hourly_launches": compare_two_hourly_launches,
            "compare_two_hourly_shelter": compare_two_hourly_shelter,
            "compare_two_stats": compare_two_stats,
            "shelter_durations": shelter_filtered.sort_values("shelter_minutes", ascending=False).to_dict(orient="records"),
        },
        "rows": rows,
    }

    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
