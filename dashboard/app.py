"""
Store Intelligence Dashboard
A professional, modern Streamlit dashboard displaying key retail metrics, visitor funnels, occupancy trends, and operational anomalies.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List
import requests
import streamlit as st
import pandas as pd
import altair as alt

# ---------------------------------------------------------------------------
# Page Configuration (Must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Store Intelligence Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Custom CSS for Premium Design & Visual Polish
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Font Setup */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif !important;
    }

    /* Metric Card Styling override */
    div[data-testid="stMetric"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 20px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border-color: #6366f1;
        box-shadow: 0 12px 20px -8px rgba(99, 102, 241, 0.4);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }
    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }

    /* Custom Alert Card styling for feed */
    .anomaly-card {
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 12px;
        border-left: 6px solid;
        background: rgba(30, 41, 59, 0.6);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(8px);
        transition: transform 0.15s ease;
    }
    .anomaly-card:hover {
        transform: scale(1.01);
    }
    .anomaly-high {
        background-color: rgba(127, 29, 29, 0.4);
        border-left-color: #ef4444;
        color: #fee2e2;
    }
    .anomaly-medium {
        background-color: rgba(124, 45, 18, 0.4);
        border-left-color: #f97316;
        color: #ffedd5;
    }
    .anomaly-low {
        background-color: rgba(20, 83, 45, 0.4);
        border-left-color: #22c55e;
        color: #dcfce7;
    }

    /* Scrollbar Styling for scrolling containers */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.3);
    }
    ::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #6366f1;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Path Resolutions & Data Helpers
# ---------------------------------------------------------------------------
API_BASE_URL = "http://127.0.0.1:8000"

def get_paths() -> Dict[str, Path]:
    """Resolve paths to JSON and SQLite databases for offline fallbacks."""
    workspace_dir = Path(__file__).resolve().parent.parent
    return {
        "analytics": workspace_dir / "store_intelligence" / "analytics.json",
        "funnel": workspace_dir / "store_intelligence" / "funnel.json",
        "anomalies_json": workspace_dir / "store_intelligence" / "anomalies.json",
        "db": workspace_dir / "store_intelligence" / "anomalies.db",
        "events": workspace_dir / "store_intelligence" / "events.json"
    }

def check_api_health() -> Dict[str, Any]:
    """Verifies health of the FastAPI backend."""
    url = f"{API_BASE_URL}/health"
    try:
        r = requests.get(url, timeout=1.0)
        if r.status_code == 200:
            return {"online": True, "details": r.json()}
    except Exception:
        pass
    return {"online": False, "details": None}

# ---------------------------------------------------------------------------
# Local Offline Fallback Loaders
# ---------------------------------------------------------------------------
def load_local_metrics(analytics_path: Path) -> Dict[str, Any]:
    """Loads metrics from local analytics.json as fallback."""
    if analytics_path.exists():
        try:
            with analytics_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "total_entries": int(data.get("total_entries", 0)),
                    "total_exits": int(data.get("total_exits", 0)),
                    "unique_visitors": int(data.get("unique_visitors", 0)),
                    "peak_occupancy": int(data.get("peak_occupancy", 0)),
                    "avg_visit_duration": float(data.get("avg_visit_duration", 0.0))
                }
        except Exception:
            pass
    return {
        "total_entries": 0,
        "total_exits": 0,
        "unique_visitors": 0,
        "peak_occupancy": 0,
        "avg_visit_duration": 0.0
    }

def load_local_funnel(funnel_path: Path) -> Dict[str, Any]:
    """Loads conversion funnel metrics from local funnel.json as fallback."""
    if funnel_path.exists():
        try:
            with funnel_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "total_passersby": 0,
        "entered_store": 0,
        "browsed_aisle": 0,
        "checkout": 0,
        "conversion_rates": {
            "entry_rate": 0.0,
            "browse_rate": 0.0,
            "purchase_rate": 0.0
        }
    }

def load_raw_anomalies(db_path: Path, json_path: Path) -> List[Dict[str, Any]]:
    """Loads raw anomalies from database or falls back to anomalies.json."""
    anomalies = []
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, type, severity, timestamp, person_id, duration_seconds, details "
                "FROM anomalies ORDER BY id DESC"
            )
            rows = cursor.fetchall()
            for r in rows:
                details_dict = None
                if r[6]:
                    try:
                        details_dict = json.loads(r[6])
                    except Exception:
                        pass
                anomalies.append({
                    "id": r[0],
                    "type": r[1],
                    "severity": r[2] or "medium",
                    "timestamp": r[3] or "Unknown",
                    "person_id": r[4],
                    "duration_seconds": r[5],
                    "details": details_dict
                })
            conn.close()
            if anomalies:
                return anomalies
        except Exception:
            pass

    if json_path.exists():
        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for idx, a in enumerate(data):
                        anomalies.append({
                            "id": idx + 1,
                            "type": a.get("type", "unknown"),
                            "severity": a.get("severity", "medium"),
                            "timestamp": a.get("timestamp", "Unknown"),
                            "person_id": a.get("person_id"),
                            "duration_seconds": a.get("duration_seconds"),
                            "details": a.get("details")
                        })
        except Exception:
            pass
    return anomalies

def load_local_anomalies(db_path: Path, json_path: Path) -> Dict[str, Any]:
    """Loads anomalies summary and detail list from local files as fallback."""
    raw_list = load_raw_anomalies(db_path, json_path)
    total = len(raw_list)
    crowding = sum(1 for a in raw_list if a.get("type") == "crowding")
    loitering = sum(1 for a in raw_list if a.get("type") == "loitering")
    traffic_spikes = sum(1 for a in raw_list if a.get("type") == "traffic_spike")
    return {
        "summary": {
            "total_anomalies": total,
            "crowding": crowding,
            "loitering": loitering,
            "traffic_spikes": traffic_spikes
        },
        "anomalies": raw_list
    }

def load_local_occupancy(analytics_path: Path) -> Dict[str, Any]:
    """Loads occupancy timeline from local analytics.json as fallback."""
    if analytics_path.exists():
        try:
            with analytics_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return {"timeline": data.get("occupancy_over_time", [])}
        except Exception:
            pass
    return {"timeline": []}

def load_local_visitors(events_path: Path) -> Dict[str, Any]:
    """Loads visitor track statistics from local events.json as fallback."""
    if events_path.exists():
        try:
            with events_path.open("r", encoding="utf-8") as f:
                events = json.load(f)
            visitors_map = {}
            for ev in events:
                p_id = ev.get("person_id")
                if p_id is None:
                    continue
                dur = ev.get("track_duration", 0.0)
                if p_id not in visitors_map:
                    visitors_map[p_id] = {"duration": dur, "events_count": 0}
                visitors_map[p_id]["events_count"] += 1
                visitors_map[p_id]["duration"] = max(visitors_map[p_id]["duration"], dur)
            
            if visitors_map:
                items = [
                    {
                        "person_id": int(p_id),
                        "track_duration": round(info["duration"], 1),
                        "events_count": info["events_count"]
                    }
                    for p_id, info in visitors_map.items()
                ]
                durations = [info["duration"] for info in visitors_map.values()]
                total = len(visitors_map)
                avg = round(sum(durations) / total, 1) if total > 0 else 0.0
                longest = round(max(durations), 1) if total > 0 else 0.0
                return {
                    "total_visitors": total,
                    "avg_duration": avg,
                    "longest_duration": longest,
                    "visitors": items
                }
        except Exception:
            pass
    return {
        "total_visitors": 0,
        "avg_duration": 0.0,
        "longest_duration": 0.0,
        "visitors": []
    }

# ---------------------------------------------------------------------------
# Endpoint Data Fetchers with Fallbacks
# ---------------------------------------------------------------------------
def get_metrics_data(paths: Dict[str, Path], online: bool) -> Dict[str, Any]:
    if online:
        try:
            r = requests.get(f"{API_BASE_URL}/metrics", timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return load_local_metrics(paths["analytics"])

def get_funnel_data(paths: Dict[str, Path], online: bool) -> Dict[str, Any]:
    if online:
        try:
            r = requests.get(f"{API_BASE_URL}/funnel", timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return load_local_funnel(paths["funnel"])

def get_anomalies_data(paths: Dict[str, Path], online: bool) -> Dict[str, Any]:
    if online:
        try:
            r = requests.get(f"{API_BASE_URL}/anomalies", timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return load_local_anomalies(paths["db"], paths["anomalies_json"])

def get_occupancy_data(paths: Dict[str, Path], online: bool) -> Dict[str, Any]:
    if online:
        try:
            r = requests.get(f"{API_BASE_URL}/occupancy", timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return load_local_occupancy(paths["analytics"])

def get_visitors_data(paths: Dict[str, Path], online: bool) -> Dict[str, Any]:
    if online:
        try:
            r = requests.get(f"{API_BASE_URL}/visitors", timeout=1.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
    return load_local_visitors(paths["events"])

# ---------------------------------------------------------------------------
# Global Session State and Core Loading
# ---------------------------------------------------------------------------
paths = get_paths()
health_info = check_api_health()
api_online = health_info["online"]

# Retrieve all datasets globally so page switching is incredibly snappy and synchronized
metrics = get_metrics_data(paths, api_online)
funnel = get_funnel_data(paths, api_online)
anomalies_payload = get_anomalies_data(paths, api_online)
occupancy = get_occupancy_data(paths, api_online)
visitors = get_visitors_data(paths, api_online)

# Determine current occupancy from timeline
timeline_list = occupancy.get("timeline", [])
current_occupancy = timeline_list[-1]["occupancy"] if timeline_list else 0

# ---------------------------------------------------------------------------
# JavaScript Rerun Auto-Refresh Helper
# ---------------------------------------------------------------------------
def set_autorefresh(seconds: int):
    """Sets a client-side timer that programmatically clicks the refresh button."""
    if seconds > 0:
        st.components.v1.html(
            f"""
            <script>
                setTimeout(function() {{
                    var buttons = window.parent.document.querySelectorAll("button");
                    var refreshButton = Array.from(buttons).find(function(el) {{
                        return el.innerText.includes("Refresh Data") || el.textContent.includes("Refresh Data");
                    }});
                    if (refreshButton) {{
                        refreshButton.click();
                    }} else {{
                        window.parent.location.reload();
                    }}
                }}, {seconds * 1000});
            </script>
            """,
            height=0,
            width=0
        )

# ---------------------------------------------------------------------------
# Sidebar UI Components
# ---------------------------------------------------------------------------
st.sidebar.title("🛍️ Store Intelligence")
st.sidebar.markdown("*Retail Edge Vision Analytics*")
st.sidebar.markdown("---")

# Health / Offline Fallback Status Card
st.sidebar.subheader("🔌 API Health Status")
if api_online:
    st.sidebar.success("● ONLINE")
    st.sidebar.caption(f"**Version**: {health_info['details'].get('version', '1.0')} | **Status**: {health_info['details'].get('status', 'healthy')}")
    st.sidebar.info("Connected to live FastAPI endpoints.")
else:
    st.sidebar.warning("⚠️ OFFLINE FALLBACK")
    st.sidebar.caption("Backend at `localhost:8000` is unreachable.")
    st.sidebar.warning("Using offline local database and JSON loaders.")

st.sidebar.markdown("---")

# Auto-Refresh Control
st.sidebar.subheader("🔄 Refresh Configuration")
refresh_options = {
    "Off": 0,
    "5 Seconds": 5,
    "10 Seconds": 10,
    "30 Seconds": 30,
    "60 Seconds": 60
}
selected_refresh = st.sidebar.selectbox("Auto-Refresh Rate", list(refresh_options.keys()), index=2)
refresh_seconds = refresh_options[selected_refresh]

# Manual Refresh Button
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.rerun()

if refresh_seconds > 0:
    set_autorefresh(refresh_seconds)
    st.sidebar.caption(f"Next refresh in {refresh_seconds}s...")

st.sidebar.markdown("---")
st.sidebar.caption("Purplle Store Intelligence Challenge 2026")

# ---------------------------------------------------------------------------
# Page 1: Executive Summary
# ---------------------------------------------------------------------------
def page_executive_summary():
    st.title("📊 Store Executive Summary")
    st.caption("High-level store performance, conversion metrics, and system alert updates.")
    st.write("")

    # Primary KPI Cards Grid
    col1, col2, col3, col4, col5 = st.columns(5)
    
    entries = metrics.get("total_entries", 0)
    exits = metrics.get("total_exits", 0)
    peak = metrics.get("peak_occupancy", 0)
    uniq = metrics.get("unique_visitors", 0)
    
    # Calculate conversion metrics
    purchase_rate = funnel.get("conversion_rates", {}).get("purchase_rate", 0.0)
    purchase_rate_pct = f"{purchase_rate * 100:.1f}%"

    col1.metric(label="Total Entries", value=entries)
    col2.metric(label="Total Exits", value=exits)
    col3.metric(label="Current Occupancy", value=current_occupancy, delta=None)
    col4.metric(label="Peak Occupancy", value=peak)
    col5.metric(label="Checkout Conversion", value=purchase_rate_pct)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([7, 5])

    with col_left:
        # Mini Occupancy Sparkline / Area Chart
        st.subheader("📈 Live Occupancy Trend")
        if timeline_list:
            df_timeline = pd.DataFrame(timeline_list)
            chart = alt.Chart(df_timeline).mark_area(
                line={'color': '#6366f1', 'size': 3},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[
                        alt.GradientStop(color='rgba(99, 102, 241, 0.4)', offset=0),
                        alt.GradientStop(color='rgba(99, 102, 241, 0)', offset=1)
                    ],
                    x1=1, y1=1, x2=1, y2=0
                )
            ).encode(
                x=alt.X("time:N", title="Time Segment", sort=None),
                y=alt.Y("occupancy:Q", title="Occupancy"),
                tooltip=["time", "occupancy"]
            ).properties(
                height=260
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No occupancy timeline records available.")

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick Funnel preview
        st.subheader("🎯 Visitor Funnel Overview")
        funnel_df = pd.DataFrame([
            {"Stage": "1. Passersby", "Count": funnel.get("total_passersby", 0)},
            {"Stage": "2. Entered", "Count": funnel.get("entered_store", 0)},
            {"Stage": "3. Browsed", "Count": funnel.get("browsed_aisle", 0)},
            {"Stage": "4. Checkout", "Count": funnel.get("checkout", 0)}
        ])
        
        funnel_chart = alt.Chart(funnel_df).mark_bar(
            cornerRadiusTopRight=6,
            cornerRadiusBottomRight=6,
            color="#818cf8"
        ).encode(
            y=alt.Y("Stage:N", sort=None, title=None),
            x=alt.X("Count:Q", title="Shoppers Count"),
            tooltip=["Stage", "Count"]
        ).properties(
            height=200
        )
        st.altair_chart(funnel_chart, use_container_width=True)

    with col_right:
        # Anomaly Summary and Mini Feed
        st.subheader("🚨 Active Alerts Feed")
        anom_summary = anomalies_payload.get("summary", {})
        total_anom = anom_summary.get("total_anomalies", 0)

        # Quick severity overview cards
        sc1, sc2 = st.columns(2)
        sc1.metric("Total Anomalies", total_anom)
        sc2.metric("Loitering Alerts", anom_summary.get("loitering", 0))

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        raw_anoms = anomalies_payload.get("anomalies", [])
        if raw_anoms:
            # Display top 4 most recent anomalies
            with st.container(height=380):
                for a in raw_anoms[:4]:
                    severity = a.get("severity", "medium").lower()
                    card_class = "anomaly-medium"
                    if severity in ["high", "critical"]:
                        card_class = "anomaly-high"
                    elif severity == "low":
                        card_class = "anomaly-low"
                        
                    t_stamp = a.get("timestamp", "Unknown")
                    if "T" in t_stamp:
                        t_stamp = t_stamp.split("T")[1]
                        
                    st.markdown(
                        f'<div class="anomaly-card {card_class}">'
                        f'<strong>{a.get("type", "unknown").upper()} ALERT</strong> ({severity.upper()})<br>'
                        f'<small>Time: {t_stamp} | ID: {a.get("id")}</small><br>'
                        f'details: {f"Person {a.get("person_id")} loitered {a.get("duration_seconds")}s" if a.get("type") == "loitering" else f"Exceeded density limits"}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        else:
            st.success("No anomalies detected. Store operations running normally.")

# ---------------------------------------------------------------------------
# Page 2: Occupancy Analytics
# ---------------------------------------------------------------------------
def page_occupancy_analytics():
    st.title("📈 Occupancy Analytics")
    st.caption("Detailed analysis of store visitor density and occupancy trends over time.")
    st.write("")

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Occupancy", current_occupancy)
    col2.metric("Peak Occupancy", metrics.get("peak_occupancy", 0))
    col3.metric("Total Entry/Exit Ratio", f"{metrics.get('total_entries', 0)} / {metrics.get('total_exits', 0)}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Detailed Interactive Line Chart
    st.subheader("Store Occupancy Level Trend")
    if timeline_list:
        df_timeline = pd.DataFrame(timeline_list)
        
        # High fidelity occupancy line with nodes
        chart = alt.Chart(df_timeline).mark_area(
            line={'color': '#6366f1', 'size': 3},
            color=alt.Gradient(
                gradient='linear',
                stops=[
                    alt.GradientStop(color='rgba(99, 102, 241, 0.4)', offset=0),
                    alt.GradientStop(color='rgba(99, 102, 241, 0)', offset=1)
                ],
                x1=1, y1=1, x2=1, y2=0
            )
        ).encode(
            x=alt.X("time:N", title="Time Segment", sort=None),
            y=alt.Y("occupancy:Q", title="Shoppers Inside Store"),
            tooltip=["time", "occupancy"]
        ).properties(
            height=400
        ).interactive()
        
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No occupancy timeline records available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Time Segment Occupancy Breakdown Table
    st.subheader("Raw Occupancy Records")
    if timeline_list:
        df_records = pd.DataFrame(timeline_list)
        df_records.columns = ["Time Segment", "Occupancy Count"]
        
        # Display with search and sorting in native interactive dataframe
        st.dataframe(
            df_records.sort_values(by="Time Segment", ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No records to display.")

# ---------------------------------------------------------------------------
# Page 3: Conversion Funnel
# ---------------------------------------------------------------------------
def page_conversion_funnel():
    st.title("🎯 Shopper Conversion Funnel")
    st.caption("Analytical evaluation of store traffic from initial passersby down to final purchases.")
    st.write("")

    passersby = funnel.get("total_passersby", 0)
    entered = funnel.get("entered_store", 0)
    browsed = funnel.get("browsed_aisle", 0)
    checkout = funnel.get("checkout", 0)

    rates = funnel.get("conversion_rates", {})
    entry_rate = rates.get("entry_rate", 0.0) * 100
    browse_rate = rates.get("browse_rate", 0.0) * 100
    purchase_rate = rates.get("purchase_rate", 0.0) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Passersby", passersby)
    col2.metric("Entered Store", f"{entered} ({entry_rate:.1f}%)")
    col3.metric("Browsed Aisle", f"{browsed} ({browse_rate:.1f}%)")
    col4.metric("Completed Checkout", f"{checkout} ({purchase_rate:.1f}%)")

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([7, 5])

    with col_left:
        st.subheader("Funnel Stage Breakdown")
        
        # Custom Funnel Representation
        stages_data = pd.DataFrame([
            {"Stage": "1. Passersby", "Count": passersby, "Rate": "100%"},
            {"Stage": "2. Entered Store", "Count": entered, "Rate": f"{entry_rate:.1f}% entry"},
            {"Stage": "3. Browsed Aisle", "Count": browsed, "Rate": f"{browse_rate:.1f}% browse"},
            {"Stage": "4. Checked Out", "Count": checkout, "Rate": f"{purchase_rate:.1f}% purchase"}
        ])

        funnel_chart = alt.Chart(stages_data).mark_bar(
            cornerRadiusTopRight=6,
            cornerRadiusBottomRight=6,
        ).encode(
            y=alt.Y("Stage:N", sort=None, title=None),
            x=alt.X("Count:Q", title="Shoppers Count"),
            color=alt.Color("Stage:N", scale=alt.Scale(
                domain=["1. Passersby", "2. Entered Store", "3. Browsed Aisle", "4. Checked Out"],
                range=["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"]
            ), legend=None),
            tooltip=["Stage", "Count", "Rate"]
        ).properties(
            height=300
        )
        st.altair_chart(funnel_chart, use_container_width=True)

    with col_right:
        st.subheader("Funnel Conversion & Leakage Table")
        
        # Build Conversion table calculations
        funnel_metrics = []
        if passersby > 0:
            # Passerby -> Entry
            funnel_metrics.append({
                "Transition": "Passersby ➔ Entered",
                "Input Count": passersby,
                "Converted": entered,
                "Conversion Rate": f"{(entered/passersby)*100:.1f}%",
                "Drop-off / Leakage": f"{((passersby-entered)/passersby)*100:.1f}%"
            })
        if entered > 0:
            # Entry -> Browse
            funnel_metrics.append({
                "Transition": "Entered ➔ Browsed Aisle",
                "Input Count": entered,
                "Converted": browsed,
                "Conversion Rate": f"{(browsed/entered)*100:.1f}%",
                "Drop-off / Leakage": f"{((entered-browsed)/entered)*100:.1f}%"
            })
        if browsed > 0:
            # Browse -> Checkout
            funnel_metrics.append({
                "Transition": "Browsed ➔ Checked Out",
                "Input Count": browsed,
                "Converted": checkout,
                "Conversion Rate": f"{(checkout/browsed)*100:.1f}%",
                "Drop-off / Leakage": f"{((browsed-checkout)/browsed)*100:.1f}%"
            })

        if funnel_metrics:
            df_funnel_table = pd.DataFrame(funnel_metrics)
            st.dataframe(df_funnel_table, use_container_width=True, hide_index=True)
        else:
            st.info("Insufficient funnel data to compile transitional metrics.")

# ---------------------------------------------------------------------------
# Page 4: Anomaly Monitoring
# ---------------------------------------------------------------------------
def page_anomaly_monitoring():
    st.title("🚨 Operational Anomaly Monitoring")
    st.caption("Active monitoring of safety and operational alerts including crowding and loitering events.")
    st.write("")

    anom_summary = anomalies_payload.get("summary", {})
    total_anom = anom_summary.get("total_anomalies", 0)
    crowding = anom_summary.get("crowding", 0)
    loitering = anom_summary.get("loitering", 0)
    spikes = anom_summary.get("traffic_spikes", 0)

    # Anomaly Counters Grid
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Anomalies", total_anom)
    col2.metric("Crowding Incidents", crowding)
    col3.metric("Loitering Alerts", loitering)
    col4.metric("Traffic Spikes", spikes)

    st.markdown("<br>", unsafe_allow_html=True)

    # Controls/Filters for Anomaly Feed
    st.subheader("Filter Incidents")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        severity_filter = st.selectbox("Severity Level", ["All", "High", "Medium", "Low"])
    with filter_col2:
        type_filter = st.selectbox("Anomaly Type", ["All", "loitering", "crowding", "traffic_spike"])
    with filter_col3:
        sort_order = st.selectbox("Sort Order", ["Newest First", "Oldest First"])

    # Load and filter list
    anomalies_list = anomalies_payload.get("anomalies", [])
    
    # Apply filters
    filtered_anoms = anomalies_list
    if severity_filter != "All":
        filtered_anoms = [a for a in filtered_anoms if a.get("severity", "").lower() == severity_filter.lower()]
    if type_filter != "All":
        filtered_anoms = [a for a in filtered_anoms if a.get("type", "").lower() == type_filter.lower()]
        
    # Apply sort
    if sort_order == "Newest First":
        # Assumed loaded sorted desc already, otherwise sort by ID
        filtered_anoms = sorted(filtered_anoms, key=lambda x: x.get("id", 0), reverse=True)
    else:
        filtered_anoms = sorted(filtered_anoms, key=lambda x: x.get("id", 0))

    st.markdown("---")

    col_left, col_right = st.columns([6, 6])

    with col_left:
        st.subheader("Live Operational Alerts Feed")
        if filtered_anoms:
            with st.container(height=450):
                for a in filtered_anoms:
                    severity = a.get("severity", "medium").lower()
                    card_class = "anomaly-medium"
                    if severity in ["high", "critical"]:
                        card_class = "anomaly-high"
                    elif severity == "low":
                        card_class = "anomaly-low"
                        
                    t_stamp = a.get("timestamp", "Unknown")
                    
                    st.markdown(
                        f'<div class="anomaly-card {card_class}">'
                        f'<strong>{a.get("type", "unknown").upper()} INCIDENT</strong> ({severity.upper()})<br>'
                        f'<small>Timestamp: {t_stamp} | ID: {a.get("id")} | Person ID: {a.get("person_id") or "N/A"}</small><br>'
                        f'details: {f"Person {a.get("person_id")} loitered {a.get("duration_seconds")}s" if a.get("type") == "loitering" else f"Exceeded limit: {a.get("details", {}).get("peak_occupancy", 0)} shoppers" if a.get("details") else f"Operational alert trigger"}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        else:
            st.success("No active anomalies match the current filters.")

    with col_right:
        st.subheader("Detailed Anomaly Log Table")
        if filtered_anoms:
            # Format logs for pretty presentation in dataframe
            table_data = []
            for a in filtered_anoms:
                table_data.append({
                    "ID": a.get("id"),
                    "Type": a.get("type"),
                    "Severity": a.get("severity"),
                    "Timestamp": a.get("timestamp"),
                    "Person ID": a.get("person_id") or "-",
                    "Duration (s)": a.get("duration_seconds") or "-"
                })
            df_anoms = pd.DataFrame(table_data)
            st.dataframe(df_anoms, use_container_width=True, hide_index=True)
        else:
            st.info("No log data available.")

# ---------------------------------------------------------------------------
# Page 5: Visitor Insights
# ---------------------------------------------------------------------------
def page_visitor_insights():
    st.title("👥 Visitor Analytics Insights")
    st.caption("Deep-dive exploration of individual visitor stay durations, activity levels, and track histories.")
    st.write("")

    tot_vis = visitors.get("total_visitors", 0)
    avg_dur = visitors.get("avg_duration", 0.0)
    long_dur = visitors.get("longest_duration", 0.0)

    # Visitor KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Visitors Tracked", tot_vis)
    col2.metric("Average Stay Duration", f"{avg_dur}s")
    col3.metric("Longest Stay Duration", f"{long_dur}s")

    st.markdown("<br>", unsafe_allow_html=True)

    visitor_list = visitors.get("visitors", [])
    if visitor_list:
        df_vis = pd.DataFrame(visitor_list)

        col_left, col_right = st.columns([6, 6])

        with col_left:
            st.subheader("Stay Duration Distribution")
            
            # Duration Histogram
            hist_chart = alt.Chart(df_vis).mark_bar(color="#8b5cf6").encode(
                x=alt.X("track_duration:Q", bin=alt.Bin(maxbins=15), title="Duration (Seconds)"),
                y=alt.Y("count():Q", title="Number of Shoppers"),
                tooltip=["count()", "track_duration"]
            ).properties(
                height=300
            )
            st.altair_chart(hist_chart, use_container_width=True)

        with col_right:
            st.subheader("Tracking Event Count vs. Stay Duration")
            
            # Scatter Plot showing correlation
            scatter_chart = alt.Chart(df_vis).mark_circle(size=80, color="#10b981").encode(
                x=alt.X("track_duration:Q", title="Track Duration (Seconds)"),
                y=alt.Y("events_count:Q", title="Camera Detections Count"),
                tooltip=["person_id", "track_duration", "events_count"]
            ).properties(
                height=300
            ).interactive()
            st.altair_chart(scatter_chart, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Full Visitor Log
        st.subheader("Analyzed Visitor Tracks")
        
        # Filter option
        min_dur = st.slider("Filter by Minimum Stay Duration (s)", 0.0, float(long_dur), 0.0, step=1.0)
        df_vis_filtered = df_vis[df_vis["track_duration"] >= min_dur]
        
        # Display
        df_vis_filtered.columns = ["Person ID", "Stay Duration (s)", "Camera Frame Detections"]
        st.dataframe(
            df_vis_filtered.sort_values(by="Stay Duration (s)", ascending=False),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No visitor tracking records available.")

# ---------------------------------------------------------------------------
# Navigation Router
# ---------------------------------------------------------------------------
pg = st.navigation([
    st.Page(page_executive_summary, title="Executive Summary", icon="📊"),
    st.Page(page_occupancy_analytics, title="Occupancy Analytics", icon="📈"),
    st.Page(page_conversion_funnel, title="Conversion Funnel", icon="🎯"),
    st.Page(page_anomaly_monitoring, title="Anomaly Monitoring", icon="🚨"),
    st.Page(page_visitor_insights, title="Visitor Insights", icon="👥")
])

# Execute selected page function
pg.run()
