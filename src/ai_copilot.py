"""
src/ai_copilot.py — PortPulse AI Operations Copilot
=====================================================
Deterministic decision-support layer that interprets structured results
produced by the existing deterministic engines (optimizer, congestion,
scenario_engine) and generates operator-facing insights, recommendations,
and warnings.

ARCHITECTURE
------------
This module sits DOWNSTREAM of all numerical calculation engines:

  Data
    ↓
  optimizer.py  /  congestion.py  /  scenario_engine.py
    ↓
  Structured results (dicts / DataFrames)
    ↓
  AI Operations Copilot  ← this module
    ↓
  Operator-facing insights

This module:
  • Does NOT calculate, modify, or invent numerical values.
  • Reads values that were already calculated by the engines.
  • Produces textual insights, classifications and recommendations
    grounded only in those values.
  • Is architected so a real LLM could be substituted for the
    template-based generators without changing the calling interface.

COPILOT TYPE: Deterministic rule-based decision support.
No LLM, no external API, no internet required.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

# ── Thresholds for rule-based classification ──────────────────────────────────
_WAIT_CRITICAL_H  = 12    # hours — individual vessel wait considered critical
_WAIT_HIGH_H      = 6     # hours — high wait
_WAIT_MODERATE_H  = 3     # hours — moderate wait
_DEM_HIGH_USD     = 50_000  # dollars — demurrage total flagged as significant
_UTIL_HIGH_PCT    = 40.0  # % utilization flagged as high
_CONGESTION_HIGH  = 50.0  # score — HIGH congestion threshold (mirrors congestion.py)
_CONGESTION_MED   = 25.0  # score — MEDIUM congestion threshold


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_int(val: Any, default: int = 0) -> int:
    """Return int(val) or default if val is None / NaN."""
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Return float(val) or default if val is None / NaN."""
    if val is None:
        return default
    try:
        f = float(val)
        import math
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _congestion_level_label(score: float) -> str:
    if score >= _CONGESTION_HIGH:
        return "HIGH"
    if score >= _CONGESTION_MED:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "IDLE"


def _wait_severity(hours: float) -> str:
    if hours >= _WAIT_CRITICAL_H:
        return "CRITICAL"
    if hours >= _WAIT_HIGH_H:
        return "HIGH"
    if hours >= _WAIT_MODERATE_H:
        return "MODERATE"
    return "LOW"


def _delta_direction(delta: float | None, good_if_negative: bool = True) -> str:
    """Return 'improved', 'worsened', or 'unchanged'."""
    if delta is None:
        return "unchanged"
    if delta == 0:
        return "unchanged"
    if good_if_negative:
        return "improved" if delta < 0 else "worsened"
    return "improved" if delta > 0 else "worsened"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Operational Status
# ─────────────────────────────────────────────────────────────────────────────

def build_operational_status(cong: dict) -> dict:
    """
    Summarise the current operational situation using congestion engine results.

    Parameters
    ----------
    cong : dict returned by congestion.calculate_congestion_metrics()

    Returns
    -------
    dict with keys:
        headline          str  — one-sentence status
        congestion_level  str  — HIGH / MEDIUM / LOW / IDLE
        bottleneck_berth  int
        total_waiting_h   int
        avg_wait_h        float
        max_wait_h        int
        vessels_waiting   int
        total_demurrage   int
        total_scheduled   int
        bullet_facts      list[str]  — formatted fact strings
        status_color      str  — 'red' / 'orange' / 'green'
    """
    if not cong:
        return {"headline": "Insufficient data to assess operational status.",
                "bullet_facts": [], "status_color": "gray",
                "congestion_level": "UNKNOWN", "bottleneck_berth": None,
                "total_waiting_h": 0, "avg_wait_h": 0.0, "max_wait_h": 0,
                "vessels_waiting": 0, "total_demurrage": 0, "total_scheduled": 0}

    summary       = cong["summary"].iloc[0]
    berth_metrics = cong["berth_metrics"]
    bottleneck_id = cong["bottleneck_berth"]

    top_row   = berth_metrics.iloc[0]
    top_score = _safe_float(top_row["congestion_score"])
    top_level = str(top_row.get("congestion_level", _congestion_level_label(top_score)))

    total_scheduled  = _safe_int(summary["total_scheduled"])
    total_waiting_h  = _safe_int(summary["total_waiting_hours"])
    avg_wait_h       = _safe_float(summary["avg_wait_hours"])
    max_wait_h       = _safe_int(summary["max_wait_hours"])
    vessels_waiting  = _safe_int(summary["vessels_waiting_count"])
    total_demurrage  = _safe_int(summary["total_demurrage_usd"])
    total_vessels    = _safe_int(summary["total_vessels"])

    status_color = "red" if top_level == "HIGH" else \
                   "orange" if top_level == "MEDIUM" else "green"

    headline = (
        f"Port operations are under {top_level} congestion pressure. "
        f"Berth {bottleneck_id} is the primary bottleneck "
        f"(congestion score {top_score:.2f}). "
        f"{vessels_waiting} of {total_scheduled} vessels experienced waiting, "
        f"accumulating {total_waiting_h} h of total delay."
    )

    bullet_facts = [
        f"Overall congestion level: **{top_level}** (score {top_score:.2f} at Berth {bottleneck_id})",
        f"Vessels scheduled: **{total_scheduled} / {total_vessels}**",
        f"Vessels with waiting: **{vessels_waiting}**",
        f"Total waiting time: **{total_waiting_h} h**",
        f"Average wait per vessel: **{avg_wait_h:.1f} h**",
        f"Longest individual wait: **{max_wait_h} h**",
        f"Total demurrage exposure: **${total_demurrage:,}**",
    ]

    return {
        "headline":         headline,
        "congestion_level": top_level,
        "bottleneck_berth": bottleneck_id,
        "total_waiting_h":  total_waiting_h,
        "avg_wait_h":       avg_wait_h,
        "max_wait_h":       max_wait_h,
        "vessels_waiting":  vessels_waiting,
        "total_demurrage":  total_demurrage,
        "total_scheduled":  total_scheduled,
        "bullet_facts":     bullet_facts,
        "status_color":     status_color,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Key Bottleneck Analysis
# ─────────────────────────────────────────────────────────────────────────────

def build_bottleneck_analysis(cong: dict) -> dict:
    """
    Identify and explain the primary bottleneck using congestion engine results.

    Returns
    -------
    dict with keys:
        berth_id         int
        congestion_score float
        congestion_level str
        utilization_pct  float
        queue_depth      float
        wait_pressure    float
        vessel_count     int
        wait_hours_total int
        why_it_matters   str
        affected_vessels list[str]
        explanation      str
    """
    if not cong:
        return {"berth_id": None, "explanation": "No data available.",
                "why_it_matters": "", "affected_vessels": []}

    berth_metrics = cong["berth_metrics"]
    vessel_flags  = cong["vessel_flags"]
    bottleneck_id = cong["bottleneck_berth"]

    top = berth_metrics.iloc[0]
    score     = _safe_float(top["congestion_score"])
    level     = str(top.get("congestion_level", _congestion_level_label(score)))
    util      = _safe_float(top["utilization_pct"])
    qdepth    = _safe_float(top["queue_depth_ratio"])
    wpres     = _safe_float(top["wait_pressure"])
    vcount    = _safe_int(top["vessel_count"])
    wait_tot  = _safe_int(top["wait_hours_total"])

    # Vessels at the bottleneck berth
    affected_vessels: list[str] = []
    if vessel_flags is not None and len(vessel_flags) > 0:
        at_berth = vessel_flags[vessel_flags["berth_id"] == bottleneck_id]
        affected_vessels = at_berth["vessel_id"].tolist()

    why_it_matters = (
        f"Berth {bottleneck_id} drives **{wait_tot} h** of total fleet waiting. "
        f"Its queue depth of **{qdepth:.2f}** means {int(qdepth * 100):.0f}% of "
        f"vessels at this berth had to wait for access. "
        f"Wait pressure of **{wpres:.2f}** indicates mean waiting time is "
        f"{wpres * 100:.0f}% of mean service time — a significant throughput drag. "
        f"Berth utilization is **{util:.1f}%** of the 72-hour planning horizon."
    )

    affected_str = ", ".join(affected_vessels) if affected_vessels else "none flagged"
    explanation = (
        f"**Berth {bottleneck_id}** is the most congested resource in the current plan "
        f"(score {score:.2f} — {level}). "
        f"It handles {vcount} vessel(s) and accounts for the largest share of "
        f"fleet-wide delay. "
        f"Vessels waiting at this berth: {affected_str}."
    )

    return {
        "berth_id":         bottleneck_id,
        "congestion_score": score,
        "congestion_level": level,
        "utilization_pct":  util,
        "queue_depth":      qdepth,
        "wait_pressure":    wpres,
        "vessel_count":     vcount,
        "wait_hours_total": wait_tot,
        "why_it_matters":   why_it_matters,
        "affected_vessels": affected_vessels,
        "explanation":      explanation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Priority Actions (Recommendations)
# ─────────────────────────────────────────────────────────────────────────────

def build_recommendations(cong: dict, sc_result: dict | None = None) -> list[dict]:
    """
    Generate 2–4 practical operator recommendations grounded in engine results.

    Each recommendation is a dict with:
        priority    int   — 1 = highest
        action      str   — what to do
        evidence    str   — why, citing actual calculated values
        category    str   — 'bottleneck' / 'vessel' / 'scenario' / 'monitoring'
    """
    if not cong:
        return [{"priority": 1, "action": "Insufficient engine data for recommendations.",
                 "evidence": "", "category": "info"}]

    recs: list[dict] = []
    priority_counter = 0

    summary       = cong["summary"].iloc[0]
    berth_metrics = cong["berth_metrics"]
    vessel_flags  = cong["vessel_flags"]
    bottleneck_id = cong["bottleneck_berth"]

    top_row   = berth_metrics.iloc[0]
    top_score = _safe_float(top_row["congestion_score"])
    top_level = str(top_row.get("congestion_level", _congestion_level_label(top_score)))

    max_wait_h      = _safe_int(summary["max_wait_hours"])
    total_waiting_h = _safe_int(summary["total_waiting_hours"])
    total_demurrage = _safe_int(summary["total_demurrage_usd"])
    vessels_waiting = _safe_int(summary["vessels_waiting_count"])

    # R1 — Investigate / address the bottleneck berth
    priority_counter += 1
    recs.append({
        "priority": priority_counter,
        "action": (
            f"Investigate and address the constrained capacity at **Berth {bottleneck_id}**."
        ),
        "evidence": (
            f"Berth {bottleneck_id} carries a congestion score of {top_score:.2f} ({top_level}), "
            f"accounting for the highest congestion in the fleet plan. "
            f"Its queue depth and wait pressure metrics indicate serial vessel queuing "
            f"that cascades wait time across multiple arrivals."
        ),
        "category": "bottleneck",
    })

    # R2 — Prioritise the vessel with the highest individual wait
    if vessel_flags is not None and len(vessel_flags) > 0:
        worst_vessel = vessel_flags.iloc[0]
        wv_id   = worst_vessel["vessel_id"]
        wv_wait = _safe_int(worst_vessel["wait_hours"])
        wv_dem  = _safe_int(worst_vessel["demurrage_cost"])
        wv_sev  = str(worst_vessel.get("wait_severity", _wait_severity(wv_wait)))
        priority_counter += 1
        recs.append({
            "priority": priority_counter,
            "action": (
                f"Prioritise **{wv_id}** — it carries the highest individual waiting time "
                f"({wv_wait} h, severity: {wv_sev})."
            ),
            "evidence": (
                f"{wv_id} accumulated {wv_wait} h of waiting, generating "
                f"${wv_dem:,} in demurrage exposure. "
                f"Early service or berth access would reduce this cost directly."
            ),
            "category": "vessel",
        })

    # R3 — Service-time reduction scenario (if not already showing improvement)
    if sc_result is not None:
        dm = sc_result.get("metric_deltas", {})
        wait_delta = dm.get("total_wait_hours_delta")
        dem_delta  = dm.get("total_demurrage_delta")
        if wait_delta is not None and wait_delta < 0:
            abs_wait = abs(wait_delta)
            abs_dem  = abs(_safe_int(dem_delta))
            priority_counter += 1
            recs.append({
                "priority": priority_counter,
                "action": (
                    "Evaluate the service-time reduction intervention before applying it "
                    "fleet-wide. The modeled scenario shows measurable improvement."
                ),
                "evidence": (
                    f"The current scenario reduces total waiting by **{abs_wait} h** "
                    f"and demurrage by **${abs_dem:,}**. "
                    f"Compare full Baseline vs Scenario metrics before committing to "
                    f"operational changes."
                ),
                "category": "scenario",
            })

    # R4 — Monitor emerging secondary bottleneck after scenario intervention
    if sc_result is not None:
        bb_base = sc_result.get("bottleneck_berth_baseline")
        bb_sc   = sc_result.get("bottleneck_berth_scenario")
        if bb_base is not None and bb_sc is not None and bb_base != bb_sc:
            priority_counter += 1
            recs.append({
                "priority": priority_counter,
                "action": (
                    f"Monitor **Berth {bb_sc}** closely if the intervention is applied — "
                    f"it becomes the new bottleneck after Berth {bb_base} is relieved."
                ),
                "evidence": (
                    f"After the scenario intervention, the bottleneck shifts from "
                    f"Berth {bb_base} to Berth {bb_sc}. "
                    f"Relieving one constrained resource can expose the next — "
                    f"congestion may be redistributed rather than eliminated."
                ),
                "category": "monitoring",
            })
    elif total_waiting_h > 0 and vessels_waiting > 0:
        # Generic monitoring recommendation when no scenario available
        priority_counter += 1
        recs.append({
            "priority": priority_counter,
            "action": (
                "Monitor the evolving vessel queue to detect secondary bottlenecks "
                "as arrival patterns unfold."
            ),
            "evidence": (
                f"{vessels_waiting} vessel(s) are currently waiting, "
                f"with a combined {total_waiting_h} h of delay. "
                f"Any further tightening of berth capacity could cascade into "
                f"additional berths beyond the current primary bottleneck."
            ),
            "category": "monitoring",
        })

    return recs


# ─────────────────────────────────────────────────────────────────────────────
# 4. Scenario Insight (Baseline vs Scenario comparison)
# ─────────────────────────────────────────────────────────────────────────────

def build_scenario_insight(sc_result: dict) -> dict:
    """
    Explain the difference between the baseline and the active scenario.

    Parameters
    ----------
    sc_result : dict returned by scenario_engine.run_scenario()

    Returns
    -------
    dict with keys:
        summary_sentence  str
        metric_lines      list[str]  — one line per key metric delta
        bottleneck_shift  bool
        bottleneck_warning str | None
        improvement_areas list[str]
        concern_areas     list[str]
    """
    if not sc_result:
        return {"summary_sentence": "No scenario selected.", "metric_lines": [],
                "bottleneck_shift": False, "bottleneck_warning": None,
                "improvement_areas": [], "concern_areas": []}

    bm  = sc_result.get("baseline_metrics", {})
    sm  = sc_result.get("scenario_metrics", {})
    dm  = sc_result.get("metric_deltas", {})
    bb_base = sc_result.get("bottleneck_berth_baseline")
    bb_sc   = sc_result.get("bottleneck_berth_scenario")
    sc_desc = sc_result.get("scenario_description", "")
    feasibility = sc_result.get("feasibility_status", "UNKNOWN")

    wait_delta  = dm.get("total_wait_hours_delta")
    avg_delta   = dm.get("avg_wait_hours_delta")
    max_delta   = dm.get("max_wait_hours_delta")
    dem_delta   = dm.get("total_demurrage_delta")
    bop_delta   = dm.get("total_berth_op_delta")
    cost_delta  = dm.get("total_cost_delta")

    def _sign_str(val, unit="", good_if_negative=True, fmt=",d"):
        if val is None:
            return "—"
        direction = "▼" if val < 0 else ("▲" if val > 0 else "—")
        sign_word = _delta_direction(val, good_if_negative)
        if fmt == ",d":
            return f"{direction} {abs(int(val)):,}{unit} ({sign_word})"
        return f"{direction} {abs(val):.1f}{unit} ({sign_word})"

    metric_lines = [
        f"Total waiting: **{_sign_str(wait_delta, ' h')}**",
        f"Average wait: **{_sign_str(avg_delta, ' h', fmt='.1f')}**",
        f"Maximum wait: **{_sign_str(max_delta, ' h')}**",
        f"Total demurrage: **{_sign_str(dem_delta, '$', fmt=',d')}**"
            .replace("$", "\\$"),
        f"Berth operating cost: **{_sign_str(bop_delta, '$', fmt=',d')}**"
            .replace("$", "\\$"),
        f"Combined cost: **{_sign_str(cost_delta, '$', fmt=',d')}**"
            .replace("$", "\\$"),
    ]
    # Fix formatting: dollar sign shouldn't be escaped in Markdown
    metric_lines = [l.replace("\\$", "$") for l in metric_lines]

    improvement_areas = []
    concern_areas = []
    for delta_key, label, good_negative in [
        ("total_wait_hours_delta",  "total waiting time", True),
        ("total_demurrage_delta",   "demurrage cost",     True),
        ("total_cost_delta",        "combined cost",      True),
        ("total_berth_op_delta",    "berth operating cost", True),
    ]:
        v = dm.get(delta_key)
        if v is None:
            continue
        if v < 0:
            improvement_areas.append(label)
        elif v > 0:
            concern_areas.append(label)

    # Build summary sentence
    if improvement_areas:
        improved_str = ", ".join(improvement_areas)
        summary_sentence = (
            f"The scenario ({feasibility} feasibility) improves **{improved_str}** "
            f"relative to the baseline."
        )
    elif concern_areas:
        concern_str = ", ".join(concern_areas)
        summary_sentence = (
            f"The scenario increases **{concern_str}** relative to the baseline. "
            f"Review the trade-offs before applying."
        )
    else:
        summary_sentence = (
            f"The scenario produces no measurable change in key cost metrics "
            f"relative to the baseline."
        )

    # Bottleneck shift warning
    bottleneck_shift  = (bb_base is not None and bb_sc is not None and bb_base != bb_sc)
    bottleneck_warning = None
    if bottleneck_shift:
        bottleneck_warning = (
            f"⚠️ **Bottleneck shift detected**: The intervention reduces congestion at "
            f"Berth {bb_base}, but **Berth {bb_sc} becomes the new bottleneck**. "
            f"Monitor Berth {bb_sc} closely before applying the intervention fleet-wide."
        )

    return {
        "summary_sentence":   summary_sentence,
        "metric_lines":       metric_lines,
        "bottleneck_shift":   bottleneck_shift,
        "bottleneck_warning": bottleneck_warning,
        "improvement_areas":  improvement_areas,
        "concern_areas":      concern_areas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Main entry point — generate full copilot output
# ─────────────────────────────────────────────────────────────────────────────

def generate_copilot_insights(
    cong: dict,
    sc_result: dict | None = None,
) -> dict:
    """
    Generate the full AI Operations Copilot output from engine results.

    Parameters
    ----------
    cong      : dict from congestion.calculate_congestion_metrics()
    sc_result : dict from scenario_engine.run_scenario()  (optional)

    Returns
    -------
    dict with keys:
        operational_status   dict  — from build_operational_status()
        bottleneck_analysis  dict  — from build_bottleneck_analysis()
        recommendations      list  — from build_recommendations()
        scenario_insight     dict  — from build_scenario_insight()  (or None)
        copilot_type         str   — "Deterministic Rule-Based Decision Support"
        disclaimer           str
    """
    operational_status  = build_operational_status(cong)
    bottleneck_analysis = build_bottleneck_analysis(cong)
    recommendations     = build_recommendations(cong, sc_result)
    scenario_insight    = build_scenario_insight(sc_result) if sc_result else None

    return {
        "operational_status":  operational_status,
        "bottleneck_analysis": bottleneck_analysis,
        "recommendations":     recommendations,
        "scenario_insight":    scenario_insight,
        "copilot_type":        "Deterministic Rule-Based Decision Support",
        "disclaimer": (
            "All insights are derived from the deterministic optimizer and "
            "congestion engine outputs. No numerical values are fabricated. "
            "This is NOT a trained predictive model and does NOT use a live "
            "port data feed or external LLM/API."
        ),
    }
