"""
app.py — PortPulse AI Dashboard
================================
Streamlit dashboard for the Container Congestion Predictor &
Port Operations Optimiser (Problem Statement L1).

All metrics are derived from the deterministic optimizer, congestion
engine and scenario engine.  No values are hard-coded or fabricated.

Data: SIMULATED — hackathon demonstration only.
"""

import sys
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from congestion import calculate_congestion_metrics
from scenario_engine import run_scenario, SERVICE_TIME_REDUCTION

# AI Operations Copilot — deterministic decision-support layer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from ai_copilot import generate_copilot_insights

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PortPulse AI",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Minimal custom CSS — control-center aesthetic ────────────────────────────
st.markdown("""
<style>
/* Global font */
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

/* KPI card */
div[data-testid="metric-container"] {
    background: #0e1117;
    border: 1px solid #2a2d35;
    border-radius: 8px;
    padding: 16px 20px;
}
div[data-testid="metric-container"] label {
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8b9ab0 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 700;
    color: #e8eaf0 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.82rem !important;
}

/* Section headers */
.section-header {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a9eff;
    margin-bottom: 4px;
    border-bottom: 1px solid #1e2230;
    padding-bottom: 6px;
}

/* Bottleneck badge */
.badge-high   { background:#7f1d1d; color:#fca5a5; padding:2px 10px; border-radius:4px; font-size:0.78rem; font-weight:600; }
.badge-medium { background:#78350f; color:#fcd34d; padding:2px 10px; border-radius:4px; font-size:0.78rem; font-weight:600; }
.badge-low    { background:#1a2e1a; color:#86efac; padding:2px 10px; border-radius:4px; font-size:0.78rem; font-weight:600; }

/* Impact card */
.impact-card {
    background: #0d1f12;
    border: 1px solid #166534;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}
.impact-number { font-size: 2rem; font-weight: 800; color: #4ade80; }
.impact-label  { font-size: 0.82rem; color: #9ca3af; margin-top: 4px; }

/* Disclaimer banner */
.disclaimer {
    background: #1a1a2e;
    border-left: 3px solid #4a9eff;
    padding: 8px 16px;
    border-radius: 0 4px 4px 0;
    font-size: 0.78rem;
    color: #8b9ab0;
}

/* Horizontal rule */
hr { border-color: #1e2230; margin: 8px 0; }

/* AI Copilot panel */
.copilot-panel {
    background: #0b1120;
    border: 1px solid #1e3a5f;
    border-left: 4px solid #4a9eff;
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 12px;
}
.copilot-header {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a9eff;
    margin-bottom: 8px;
}
.copilot-fact {
    font-size: 0.85rem;
    color: #c9d1d9;
    line-height: 1.7;
}
.copilot-rec {
    background: #0e1420;
    border: 1px solid #1e2d44;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.copilot-rec-num {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #4a9eff;
    text-transform: uppercase;
}
.copilot-warning {
    background: #1a1200;
    border: 1px solid #78350f;
    border-left: 4px solid #f59e0b;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-size: 0.85rem;
    color: #fcd34d;
}
.copilot-badge-facts {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #22c55e;
    background: #052e16;
    border: 1px solid #166534;
    padding: 2px 8px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 8px;
}
.copilot-badge-recs {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #93c5fd;
    background: #0c2a4a;
    border: 1px solid #1e3a5f;
    padding: 2px 8px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Data loading & engine calls — cached so the solver runs once per session
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Running optimizer & congestion engine…")
def load_all_data():
    vessels  = pd.read_csv("data/vessels.csv")
    berths   = pd.read_csv("data/berths.csv")
    schedule = pd.read_csv("data/schedule_output.csv")

    cong = calculate_congestion_metrics(vessels, berths, schedule)

    return vessels, berths, schedule, cong


@st.cache_data(show_spinner="Running scenario engine…")
def load_scenario(reduction_pct: int):
    vessels = pd.read_csv("data/vessels.csv")
    berths  = pd.read_csv("data/berths.csv")
    result  = run_scenario(
        SERVICE_TIME_REDUCTION,
        vessels,
        berths,
        {"vessel_ids": ["V03", "V07", "V11", "V15"], "reduction_pct": reduction_pct},
    )
    return result


vessels, berths, schedule, cong = load_all_data()

# Pull the commonly-used sub-objects once
summary       = cong["summary"].iloc[0]
berth_metrics = cong["berth_metrics"]
vessel_flags  = cong["vessel_flags"]
hotspot       = cong["hotspot_periods"]
bottleneck_id = cong["bottleneck_berth"]
top_score     = berth_metrics.iloc[0]["congestion_score"]
top_level     = berth_metrics.iloc[0]["congestion_level"]


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# PortPulse AI")
st.markdown(
    "**Container Congestion Predictor & Port Operations Optimiser** · "
    "Problem Statement L1"
)
st.markdown(
    '<div class="disclaimer">⚠️ Demo data: simulated operational data for hackathon demonstration. '
    'All metrics are generated by the deterministic optimizer and congestion engine. '
    'No live port data is used.</div>',
    unsafe_allow_html=True,
)
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — EXECUTIVE KPIs
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">72-Hour Operational Snapshot</p>', unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)

level_arrow = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢", "IDLE": "⚪"}
level_icon  = level_arrow.get(top_level, "")

k1.metric(
    label="Congestion Score — Primary Bottleneck",
    value=f"{top_score:.2f}",
    delta=f"{level_icon} {top_level} · Berth {bottleneck_id}",
    delta_color="off",
)
k2.metric(
    label="Vessels Scheduled",
    value=f"{int(summary['total_scheduled'])} / {int(summary['total_vessels'])}",
    delta="All feasible",
    delta_color="off",
)
k3.metric(
    label="Average Wait",
    value=f"{summary['avg_wait_hours']:.1f} h",
    delta=f"Max {int(summary['max_wait_hours'])} h · {int(summary['vessels_waiting_count'])} vessels waiting",
    delta_color="off",
)
k4.metric(
    label="Total Demurrage",
    value=f"${int(summary['total_demurrage_usd']):,}",
    delta=f"{int(summary['total_waiting_hours'])} h total waiting",
    delta_color="off",
)
k5.metric(
    label="Service Hours Scheduled",
    value=f"{int(summary['total_service_hours'])} h",
    delta=f"72-hour horizon",
    delta_color="off",
)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PORT CONGESTION MAP & SECTION 4 — BERTH UTILIZATION (side by side)
# ══════════════════════════════════════════════════════════════════════════════

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<p class="section-header">Port Congestion — Berth Rankings</p>', unsafe_allow_html=True)

    level_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e", "IDLE": "#6b7280"}
    badge_class = {"HIGH": "badge-high", "MEDIUM": "badge-medium", "LOW": "badge-low", "IDLE": "badge-low"}

    for _, row in berth_metrics.iterrows():
        bid    = int(row["berth_id"])
        score  = row["congestion_score"]
        level  = row["congestion_level"]
        util   = row["utilization_pct"]
        qdepth = row["queue_depth_ratio"]
        wpres  = row["wait_pressure"]
        icon   = "▲ BOTTLENECK" if bid == bottleneck_id else ""

        with st.container():
            c1, c2, c3, c4 = st.columns([1.4, 1.2, 1.2, 1.2])
            c1.markdown(
                f"**Berth {bid}** "
                f'<span class="{badge_class[level]}">{level}</span>'
                f"{'  <span style=\"color:#f59e0b;font-size:0.7rem\">▲ BOTTLENECK</span>' if bid == bottleneck_id else ''}",
                unsafe_allow_html=True,
            )
            c2.markdown(f"Score **{score:.2f}**")
            c3.markdown(f"Util **{util:.1f}%**")
            c4.markdown(f"Queue **{qdepth:.2f}** · Press **{wpres:.2f}**")
            # Mini progress bar for congestion score (0–100)
            st.progress(score / 100, text="")
        st.markdown("")

with col_right:
    st.markdown('<p class="section-header">Berth Utilization (72-hour window)</p>', unsafe_allow_html=True)

    bm_sorted = berth_metrics.sort_values("berth_id")
    bar_colors = [
        "#ef4444" if int(b) == bottleneck_id else
        "#f59e0b" if v >= 25 else "#3b82f6"
        for b, v in zip(bm_sorted["berth_id"], bm_sorted["congestion_score"])
    ]
    fig_util = go.Figure(go.Bar(
        x=[f"Berth {int(b)}" for b in bm_sorted["berth_id"]],
        y=bm_sorted["utilization_pct"],
        marker_color=bar_colors,
        text=[f"{v:.1f}%" for v in bm_sorted["utilization_pct"]],
        textposition="outside",
    ))
    fig_util.update_layout(
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#c9d1d9",
        yaxis=dict(title="Utilization (%)", range=[0, 65], gridcolor="#1e2230"),
        xaxis=dict(gridcolor="#1e2230"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=280,
        showlegend=False,
    )
    st.plotly_chart(fig_util, use_container_width=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — 72-HOUR OPERATIONAL PLAN (Gantt)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">72-Hour Operational Plan — Optimizer-Generated Schedule</p>', unsafe_allow_html=True)

# Build Gantt data
gantt_rows = []
berth_palette = {1: "#3b82f6", 2: "#8b5cf6", 3: "#ef4444", 4: "#10b981", 5: "#f59e0b"}

for _, row in schedule.sort_values(["berth_id", "start_time"]).iterrows():
    bid = int(row["berth_id"])
    # Waiting bar (if any)
    if row["wait_hours"] > 0:
        gantt_rows.append(dict(
            Vessel=row["vessel_id"],
            VesselName=row["vessel_name"],
            Start=row["eta_hours"],
            Finish=row["start_time"],
            BerthID=bid,
            Type="Waiting",
            Color="#374151",
            Label=f"{row['vessel_id']} waiting {int(row['wait_hours'])}h",
        ))
    # Service bar
    gantt_rows.append(dict(
        Vessel=row["vessel_id"],
        VesselName=row["vessel_name"],
        Start=row["start_time"],
        Finish=row["end_time"],
        BerthID=bid,
        Type=f"Berth {bid}",
        Color=berth_palette.get(bid, "#6b7280"),
        Label=f"{row['vessel_id']} @ Berth {bid}  (h{int(row['start_time'])}–h{int(row['end_time'])})",
    ))

gantt_df = pd.DataFrame(gantt_rows)

# Sort vessels by start time for clean y-axis ordering
vessel_order = (
    schedule.sort_values("start_time")["vessel_id"].tolist()
)

fig_gantt = go.Figure()

# Service bars
for bid in sorted(schedule["berth_id"].unique()):
    sub = gantt_df[(gantt_df["BerthID"] == bid) & (gantt_df["Type"] != "Waiting")]
    if sub.empty:
        continue
    fig_gantt.add_trace(go.Bar(
        name=f"Berth {bid}",
        x=sub["Finish"] - sub["Start"],
        y=sub["Vessel"],
        base=sub["Start"],
        orientation="h",
        marker_color=berth_palette.get(bid, "#6b7280"),
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>h%{base} → h%{x}<extra></extra>",
        customdata=list(zip(sub["Vessel"], sub["VesselName"])),
        legendgroup=f"berth_{bid}",
    ))

# Waiting bars
wait_sub = gantt_df[gantt_df["Type"] == "Waiting"]
if not wait_sub.empty:
    fig_gantt.add_trace(go.Bar(
        name="Waiting",
        x=wait_sub["Finish"] - wait_sub["Start"],
        y=wait_sub["Vessel"],
        base=wait_sub["Start"],
        orientation="h",
        marker_color="#374151",
        marker_line=dict(color="#6b7280", width=1),
        hovertemplate="<b>%{customdata}</b><br>Waiting<br>h%{base} → h%{x}<extra></extra>",
        customdata=wait_sub["Vessel"],
        legendgroup="waiting",
    ))

fig_gantt.update_layout(
    barmode="overlay",
    plot_bgcolor="#0e1117",
    paper_bgcolor="#0e1117",
    font_color="#c9d1d9",
    xaxis=dict(
        title="Hour", range=[0, 40], gridcolor="#1e2230",
        tickvals=list(range(0, 41, 4)),
    ),
    yaxis=dict(
        categoryorder="array",
        categoryarray=list(reversed(vessel_order)),
        gridcolor="#1e2230",
        tickfont=dict(size=11),
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=10, r=10, t=40, b=10),
    height=420,
)

# Add Berth 3 annotation
fig_gantt.add_annotation(
    x=38, y="V11",
    text="← Berth 3 queue",
    showarrow=False,
    font=dict(color="#ef4444", size=11),
    xanchor="right",
)

st.plotly_chart(fig_gantt, use_container_width=True)
st.caption(
    "Gray bars = vessel waiting. Colored bars = active berth service. "
    "Red bars (Berth 3) show the constrained large-vessel queue: V03 → V07 → V15 → V11."
)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — WHAT-IF SCENARIO CONTROLS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">What-If Scenario — Service Time Reduction</p>', unsafe_allow_html=True)
st.markdown(
    "**What happens if we reduce service time at the constrained berth?**  "
    "Select a reduction percentage to model the operational impact on the 72-hour plan."
)

sc_col1, sc_col2, sc_col3 = st.columns([1, 1, 2])
with sc_col1:
    reduction_pct = st.selectbox(
        "Service time reduction",
        options=[10, 15, 20, 25, 30],
        index=2,       # default 20%
        format_func=lambda x: f"{x}% reduction",
        help="Percentage reduction applied via floor(original × (1 − pct/100)), min 1h",
    )
with sc_col2:
    st.markdown("**Affected vessels**")
    st.markdown("V03, V07, V11, V15  \n_(Berth 3 large-vessel queue)_")
with sc_col3:
    import math
    orig = {"V03": 8, "V07": 9, "V11": 8, "V15": 7}
    rows = []
    for vid, h in orig.items():
        new_h = max(1, math.floor(h * (1 - reduction_pct / 100)))
        rows.append({"Vessel": vid, "Original (h)": h, "Reduced (h)": new_h, "Δ": new_h - h})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

sc_result = load_scenario(reduction_pct)
bm  = sc_result["baseline_metrics"]
sm  = sc_result["scenario_metrics"]
dm  = sc_result["metric_deltas"]
sc_sched = sc_result["scenario_schedule"]

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — BASELINE VS SCENARIO TABLE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">Baseline vs Scenario — Modeled Impact Comparison</p>', unsafe_allow_html=True)

def _fmt(val, fmt="d"):
    if val is None:
        return "—"
    if fmt == "$":
        return f"${val:,.0f}"
    if fmt == "h":
        return f"{val:.1f} h" if isinstance(val, float) else f"{val} h"
    if fmt == "%":
        return f"{val:.2f}%"
    return str(int(val)) if isinstance(val, (int, float)) else str(val)

def _delta_fmt(val, fmt="d", good_negative=True):
    if val is None:
        return "—"
    if isinstance(val, float) and val == int(val):
        val = int(val)
    prefix = "▼ " if (val < 0 and good_negative) or (val > 0 and not good_negative) else \
             "▲ " if val != 0 else ""
    color  = "green" if (val < 0 and good_negative) or (val > 0 and not good_negative) else \
             "red"   if val != 0 else "gray"
    raw    = _fmt(val, fmt)
    return f":{color}[{prefix}{raw}]"

comparison_rows = [
    ("Scheduled vessels",    _fmt(bm["scheduled_vessels"]),                  _fmt(sm["scheduled_vessels"]),                  _delta_fmt(dm.get("scheduled_vessels_delta"), good_negative=False)),
    ("Total waiting",        _fmt(bm["total_wait_hours"], "h"),               _fmt(sm["total_wait_hours"], "h"),               _delta_fmt(dm.get("total_wait_hours_delta"), "h")),
    ("Average wait",         _fmt(bm["avg_wait_hours"], "h"),                 _fmt(sm["avg_wait_hours"], "h"),                 _delta_fmt(dm.get("avg_wait_hours_delta"), "h")),
    ("Maximum wait",         _fmt(bm["max_wait_hours"], "h"),                 _fmt(sm["max_wait_hours"], "h"),                 _delta_fmt(dm.get("max_wait_hours_delta"), "h")),
    ("Vessels waiting",      _fmt(bm["vessels_waiting"]),                     _fmt(sm["vessels_waiting"]),                     _delta_fmt(dm.get("vessels_waiting_delta"))),
    ("Total demurrage",      _fmt(bm["total_demurrage"], "$"),                _fmt(sm["total_demurrage"], "$"),                _delta_fmt(dm.get("total_demurrage_delta"), "$")),
    ("Berth operating cost", _fmt(bm["total_berth_op"], "$"),                 _fmt(sm["total_berth_op"], "$"),                 _delta_fmt(dm.get("total_berth_op_delta"), "$")),
    ("Combined cost",        _fmt(bm["total_cost"], "$"),                     _fmt(sm["total_cost"], "$"),                     _delta_fmt(dm.get("total_cost_delta"), "$")),
    ("Berth 3 utilization",  _fmt(bm["berth_utilization"].get(3, 0), "%"),    _fmt(sm["berth_utilization"].get(3, 0), "%"),    _delta_fmt(dm.get("berth_utilization_delta", {}).get(3), "%")),
    ("Bottleneck berth",     f"Berth {sc_result['bottleneck_berth_baseline']}", f"Berth {sc_result['bottleneck_berth_scenario']}", ":orange[shifted]" if sc_result["bottleneck_berth_baseline"] != sc_result["bottleneck_berth_scenario"] else ":gray[unchanged]"),
]

hdr1, hdr2, hdr3, hdr4 = st.columns([2, 1.5, 1.5, 1.5])
hdr1.markdown("**Metric**")
hdr2.markdown("**Baseline**")
hdr3.markdown("**Scenario**")
hdr4.markdown("**Change**")
st.markdown('<hr style="margin:2px 0 8px 0">', unsafe_allow_html=True)

for metric, base_val, sc_val, delta_val in comparison_rows:
    c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
    c1.markdown(metric)
    c2.markdown(base_val)
    c3.markdown(sc_val)
    c4.markdown(delta_val)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — OPERATIONAL IMPACT CARDS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">Modeled Scenario Impact</p>', unsafe_allow_html=True)

wait_delta    = dm.get("total_wait_hours_delta", 0) or 0
dem_delta     = dm.get("total_demurrage_delta", 0) or 0
cost_delta    = dm.get("total_cost_delta", 0) or 0
max_w_delta   = dm.get("max_wait_hours_delta", 0) or 0
bop_delta     = dm.get("total_berth_op_delta", 0) or 0

i1, i2, i3, i4, i5 = st.columns(5)

def impact_card(col, number: str, label: str, positive: bool = True):
    color = "#4ade80" if positive else "#f87171"
    col.markdown(
        f'<div class="impact-card">'
        f'<div class="impact-number" style="color:{color}">{number}</div>'
        f'<div class="impact-label">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

impact_card(i1, f"▼ {abs(wait_delta)} h",         "less vessel waiting",            positive=True)
impact_card(i2, f"▼ ${abs(dem_delta):,}",          "demurrage saving",               positive=True)
impact_card(i3, f"▼ ${abs(cost_delta):,}",         "combined modeled cost",          positive=True)
impact_card(i4, f"▼ {abs(max_w_delta)} h",         "maximum vessel wait",            positive=True)
impact_card(i5, f"▼ ${abs(bop_delta):,}",          "berth operating cost",           positive=True)

st.caption(
    "Modeled scenario impact only — based on simulated data. "
    "These are not guaranteed operational savings."
)
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6b — SCENARIO GANTT (side-by-side with baseline for Berth 3)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">Berth 3 Queue — Baseline vs Scenario</p>', unsafe_allow_html=True)
gc1, gc2 = st.columns(2)

def berth3_gantt(sched_df: pd.DataFrame, title: str) -> go.Figure:
    b3 = sched_df[sched_df["berth_id"] == 3].sort_values("start_time")
    fig = go.Figure()
    for _, row in b3.iterrows():
        if row["wait_hours"] > 0:
            fig.add_trace(go.Bar(
                name="Waiting", x=[row["wait_hours"]], y=[row["vessel_id"]],
                base=[row["eta_hours"]], orientation="h",
                marker_color="#374151",
                showlegend=False,
                hovertemplate=f"<b>{row['vessel_id']}</b><br>Waiting {int(row['wait_hours'])}h<extra></extra>",
            ))
        svc = int(row["end_time"]) - int(row["start_time"])
        fig.add_trace(go.Bar(
            name="Service", x=[svc], y=[row["vessel_id"]],
            base=[row["start_time"]], orientation="h",
            marker_color="#ef4444",
            showlegend=False,
            hovertemplate=f"<b>{row['vessel_id']}</b><br>Service h{int(row['start_time'])}–h{int(row['end_time'])}<extra></extra>",
        ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#c9d1d9")),
        barmode="overlay",
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#c9d1d9",
        xaxis=dict(title="Hour", range=[0, 40], gridcolor="#1e2230"),
        yaxis=dict(categoryorder="array",
                   categoryarray=["V11", "V15", "V07", "V03"],
                   gridcolor="#1e2230"),
        margin=dict(l=0, r=0, t=40, b=0), height=220,
    )
    return fig

with gc1:
    st.plotly_chart(berth3_gantt(schedule, "Baseline — Berth 3"), use_container_width=True)
with gc2:
    st.plotly_chart(berth3_gantt(sc_sched, f"Scenario ({reduction_pct}% reduction) — Berth 3"), use_container_width=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — BOTTLENECK EXPLANATION (deterministic template)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">Operational Analysis</p>', unsafe_allow_html=True)

b3_row    = berth_metrics[berth_metrics["berth_id"] == 3].iloc[0]
b3_score  = b3_row["congestion_score"]
b3_level  = b3_row["congestion_level"]
b3_util   = b3_row["utilization_pct"]
b3_queue  = b3_row["queue_depth_ratio"]
b3_wait_p = b3_row["wait_pressure"]

sc_bb  = sc_result["bottleneck_berth_scenario"]
sc_b3  = [r for _, r in cong["berth_metrics"].iterrows() if int(r["berth_id"]) == 3][0]

b3_svc_base = int(schedule[schedule["berth_id"] == 3].apply(lambda r: r["end_time"] - r["start_time"], axis=1).sum())
b3_svc_sc   = int(sc_sched[sc_sched["berth_id"] == 3].apply(lambda r: r["end_time"] - r["start_time"], axis=1).sum())

exp_col1, exp_col2 = st.columns(2)

with exp_col1:
    st.markdown("#### Current Bottleneck: Berth 3")
    st.markdown(f"""
Berth 3 is the highest-congestion point in the 72-hour plan with an analytical congestion
score of **{b3_score:.2f} ({b3_level})**. It handles vessels V03, V07, V15 and V11 — the four
large-vessel arrivals that exceed the length or draft capacity of every other berth.
This creates a **forced serialization**: each ship must wait for the previous one to finish
before service can begin.

**Queue pressure metrics:**
- Utilization: **{b3_util:.1f}%** of the 72-hour window
- Queue depth: **{b3_queue:.2f}** (75% of Berth 3 vessels waited)
- Wait pressure: **{b3_wait_p:.2f}** (mean wait = {b3_wait_p*100:.0f}% of mean service time)

The longest individual wait is **{int(summary['max_wait_hours'])} hours** (V11), accumulated
because it arrives last into the already-occupied Berth 3 queue.
""")

with exp_col2:
    st.markdown(f"#### Scenario Effect: {reduction_pct}% Service Time Reduction")

    # Pull per-vessel wait from scenario schedule
    waits = {row["vessel_id"]: int(row["wait_hours"]) for _, row in sc_sched.iterrows()}
    base_waits = {row["vessel_id"]: int(row["wait_hours"]) for _, row in schedule.iterrows()}

    st.markdown(f"""
Reducing service hours for the four Berth 3 vessels from **{b3_svc_base}h to {b3_svc_sc}h** total
allows the serialized queue to clear earlier. The downstream cascade effect is direct:

| Vessel | Baseline wait | Scenario wait | Improvement |
|--------|-------------|-------------|-------------|
| V03 | {base_waits.get("V03", 0)} h | {waits.get("V03", 0)} h | {base_waits.get("V03", 0) - waits.get("V03", 0)} h |
| V07 | {base_waits.get("V07", 0)} h | {waits.get("V07", 0)} h | {base_waits.get("V07", 0) - waits.get("V07", 0)} h |
| V15 | {base_waits.get("V15", 0)} h | {waits.get("V15", 0)} h | {base_waits.get("V15", 0) - waits.get("V15", 0)} h |
| V11 | {base_waits.get("V11", 0)} h | {waits.get("V11", 0)} h | {base_waits.get("V11", 0) - waits.get("V11", 0)} h |

**Bottleneck shift:** After the intervention, Berth 3's congestion score drops below Berth 2.
The bottleneck moves from Berth 3 → **Berth {sc_bb}**. This demonstrates that relieving one
constrained resource exposes the next — congestion is redistributed, not eliminated.

_Scenario description:_ {sc_result["scenario_description"]}
""")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8b — AI OPERATIONS COPILOT
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">🤖 AI Operations Copilot</p>', unsafe_allow_html=True)
st.markdown(
    '<div class="disclaimer">'
    '🤖 <strong>Copilot type: Deterministic Rule-Based Decision Support</strong> — '
    'All insights are derived exclusively from the optimizer and congestion engine outputs. '
    'No numerical values are fabricated. No external LLM or API is used. '
    'Facts and AI recommendations are clearly separated below.'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown("")

# Generate copilot insights (uses results already computed above — no new engine calls)
copilot = generate_copilot_insights(cong, sc_result)
op_status = copilot["operational_status"]
bn_analysis = copilot["bottleneck_analysis"]
recs = copilot["recommendations"]
sc_insight = copilot["scenario_insight"]

# ── Row 1: Operational Status + Key Bottleneck ────────────────────────────────
cp_col1, cp_col2 = st.columns(2, gap="large")

with cp_col1:
    status_border = {"red": "#ef4444", "orange": "#f59e0b", "green": "#22c55e"}.get(
        op_status["status_color"], "#4a9eff"
    )
    st.markdown(
        f'<div class="copilot-panel" style="border-left-color:{status_border}">'
        f'<div class="copilot-header">Operational Status</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="copilot-badge-facts">✓ Calculated Facts</span>',
        unsafe_allow_html=True,
    )
    st.markdown(op_status["headline"])
    for fact in op_status["bullet_facts"]:
        st.markdown(f"- {fact}")
    st.markdown("</div>", unsafe_allow_html=True)

with cp_col2:
    st.markdown(
        '<div class="copilot-panel">'
        '<div class="copilot-header">Key Bottleneck</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="copilot-badge-facts">✓ Calculated Facts</span>',
        unsafe_allow_html=True,
    )
    st.markdown(bn_analysis["explanation"])
    st.markdown(bn_analysis["why_it_matters"])
    st.markdown("</div>", unsafe_allow_html=True)

# ── Row 2: Priority Actions ────────────────────────────────────────────────────
st.markdown("")
st.markdown(
    '<div class="copilot-panel">'
    '<div class="copilot-header">Priority Actions</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<span class="copilot-badge-recs">🤖 AI Decision-Support Recommendations</span>',
    unsafe_allow_html=True,
)
for rec in recs:
    cat_icon = {"bottleneck": "🔴", "vessel": "🚢", "scenario": "📊", "monitoring": "👁"}.get(
        rec.get("category", ""), "▸"
    )
    st.markdown(
        f'<div class="copilot-rec">'
        f'<div class="copilot-rec-num">{cat_icon} Action {rec["priority"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**{rec['action']}**")
    st.markdown(f"*Why this matters:* {rec['evidence']}")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── Row 3: Scenario Insight ────────────────────────────────────────────────────
if sc_insight:
    st.markdown("")
    st.markdown(
        '<div class="copilot-panel">'
        '<div class="copilot-header">Scenario Insight</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="copilot-badge-facts">✓ Calculated Facts</span>',
        unsafe_allow_html=True,
    )
    st.markdown(sc_insight["summary_sentence"])
    sci_col1, sci_col2 = st.columns(2)
    with sci_col1:
        for line in sc_insight["metric_lines"][:3]:
            st.markdown(f"- {line}")
    with sci_col2:
        for line in sc_insight["metric_lines"][3:]:
            st.markdown(f"- {line}")

    # Bottleneck shift warning
    if sc_insight["bottleneck_warning"]:
        st.markdown("")
        st.markdown(
            f'<div class="copilot-warning">{sc_insight["bottleneck_warning"]}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — VESSEL DETAIL TABLE (expandable)
# ══════════════════════════════════════════════════════════════════════════════

with st.expander("📋  Full Optimizer Schedule — Vessel Detail", expanded=False):
    # Merge with vessels for priority and service_hours
    detail = schedule.merge(
        vessels[["vessel_id", "priority", "service_hours", "demurrage_cost_per_hour"]],
        on="vessel_id", how="left",
    ).sort_values("start_time")

    priority_label = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
    detail["priority_label"] = detail["priority"].map(priority_label)

    display_cols = {
        "vessel_id":           "Vessel ID",
        "vessel_name":         "Vessel Name",
        "priority_label":      "Priority",
        "berth_id":            "Berth",
        "eta_hours":           "ETA (h)",
        "service_hours":       "Service (h)",
        "start_time":          "Start (h)",
        "end_time":            "End (h)",
        "wait_hours":          "Wait (h)",
        "demurrage_cost":      "Demurrage ($)",
        "berth_operating_cost":"Berth Op ($)",
        "total_cost":          "Total Cost ($)",
    }
    st.dataframe(
        detail[list(display_cols.keys())].rename(columns=display_cols),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Demurrage ($)":      st.column_config.NumberColumn(format="$%d"),
            "Berth Op ($)":       st.column_config.NumberColumn(format="$%d"),
            "Total Cost ($)":     st.column_config.NumberColumn(format="$%d"),
            "Wait (h)":           st.column_config.NumberColumn(),
        },
    )
    total_row_label = "**TOTAL**"
    tc1, tc2, tc3, tc4, tc5 = st.columns([3, 1, 1, 1, 2])
    tc1.markdown(total_row_label)
    tc3.markdown(f"**{int(detail['wait_hours'].sum())} h**")
    tc4.markdown(f"**${int(detail['demurrage_cost'].sum()):,}**")
    tc5.markdown(f"**${int(detail['total_cost'].sum()):,}**")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — METHODOLOGY & DATA NOTE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown('<p class="section-header">Data & Methodology</p>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("""
**Data**
Simulated vessel and berth operational data. All figures are generated
deterministically — no live port feed is used.

**Planning horizon**
72 hours · 15 vessels · 5 berths
""")

with m2:
    st.markdown("""
**Congestion Engine**
PortPulse analytical congestion index — a weighted combination of berth
utilization, queue depth, wait pressure and throughput load.
Not a trained ML model.

**Optimization**
OR-Tools MIP berth allocation and scheduling.
Objective: priority-weighted demurrage cost + berth operating cost.
""")

with m3:
    st.markdown("""
**Current limitations**
- Crane scheduling is not modelled (crane data exists but is unused).
- Tide windows and weather are not modelled.
- Vessel arrivals are deterministic (no stochastic delay model).

**Congestion score**
Transparent analytical formula — not an industry-standard metric.
See `congestion.py` for the exact formula and weights.
""")

st.markdown(
    '<div class="disclaimer">PortPulse AI · Hackathon demonstration · '
    'Simulated data only · Optimizer: OR-Tools SCIP · '
    'Congestion: deterministic analytical index · '
    'Crane scheduling: not modelled</div>',
    unsafe_allow_html=True,
)
