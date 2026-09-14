"""
congestion.py — PortPulse AI: Congestion Analysis Engine
=========================================================
Transparent, deterministic, forward-looking congestion assessment
based on the 72-hour operational plan produced by the optimizer.

This module does NOT use machine learning.
All metrics are derived directly from the scheduled service intervals,
berth capacities, and vessel attributes.  Every figure is traceable
to its input data.
"""

import pandas as pd
import numpy as np

PLANNING_HORIZON_HOURS = 72

# ── Congestion-score weight configuration ────────────────────────────────────
# These weights are transparent design choices, not trained parameters.
# They control how much each factor contributes to a berth's congestion score.
W_UTILIZATION   = 0.40   # fraction of planning horizon the berth is busy
W_QUEUE_DEPTH   = 0.25   # vessels queued / max feasible throughput
W_WAIT_PRESSURE = 0.25   # mean wait relative to mean service time at this berth
W_VESSEL_COUNT  = 0.10   # simple throughput load (vessels / horizon in days)


def calculate_congestion_metrics(
    vessels_df: pd.DataFrame,
    berths_df:  pd.DataFrame,
    schedule_df: pd.DataFrame,
) -> dict:
    """
    Compute forward-looking congestion metrics from the current 72-hour plan.

    Parameters
    ----------
    vessels_df   : DataFrame from data/vessels.csv
    berths_df    : DataFrame from data/berths.csv
    schedule_df  : DataFrame from data/schedule_output.csv (optimizer output)

    Returns
    -------
    dict with keys:
        'summary'          – one-row DataFrame of fleet-wide metrics
        'berth_metrics'    – per-berth utilization, load, congestion score
        'vessel_flags'     – vessels with significant waiting (wait > 0)
        'hotspot_periods'  – hourly port-wide occupancy across the horizon
        'bottleneck_berth' – berth_id of most congested berth (int)
        'metadata'         – description and method notes (dict)
    """

    # ── 0. Defensive copies — never mutate caller's data ─────────────────────
    vessels  = vessels_df.copy()
    berths   = berths_df.copy()
    schedule = schedule_df.copy()

    # ── 1. Fleet-wide summary metrics ────────────────────────────────────────
    total_vessels          = len(vessels)
    total_scheduled        = len(schedule)
    total_service_hours    = schedule["service_hours"].sum() if "service_hours" in schedule.columns \
                             else (schedule["end_time"] - schedule["start_time"]).sum()
    total_waiting_hours    = schedule["wait_hours"].sum()
    avg_waiting_hours      = schedule["wait_hours"].mean()
    max_waiting_hours      = schedule["wait_hours"].max()
    vessels_waiting_count  = (schedule["wait_hours"] > 0).sum()
    total_demurrage        = schedule["demurrage_cost"].sum()

    summary = pd.DataFrame([{
        "planning_horizon_hours":  PLANNING_HORIZON_HOURS,
        "total_vessels":           total_vessels,
        "total_scheduled":         total_scheduled,
        "total_service_hours":     total_service_hours,
        "total_waiting_hours":     total_waiting_hours,
        "avg_wait_hours":          round(avg_waiting_hours, 2),
        "max_wait_hours":          max_waiting_hours,
        "vessels_waiting_count":   vessels_waiting_count,
        "total_demurrage_usd":     total_demurrage,
    }])

    # ── 2. Per-berth metrics ──────────────────────────────────────────────────
    # Derive service hours from schedule if not present as a column
    sched_with_svc = schedule.copy()
    if "service_hours" not in sched_with_svc.columns:
        sched_with_svc["service_hours"] = (
            sched_with_svc["end_time"] - sched_with_svc["start_time"]
        )

    berth_rows = []
    for _, berth in berths.iterrows():
        bid = berth["berth_id"]
        assigned = sched_with_svc[sched_with_svc["berth_id"] == bid]

        vessel_count      = len(assigned)
        svc_hours_total   = assigned["service_hours"].sum()
        wait_hours_total  = assigned["wait_hours"].sum()
        wait_hours_mean   = assigned["wait_hours"].mean() if vessel_count > 0 else 0.0
        wait_hours_max    = assigned["wait_hours"].max()  if vessel_count > 0 else 0
        svc_hours_mean    = assigned["service_hours"].mean() if vessel_count > 0 else 0.0

        # Berth utilization: fraction of the 72-hour window occupied
        utilization_pct   = round(100.0 * svc_hours_total / PLANNING_HORIZON_HOURS, 2)

        # Queue depth: vessels waiting / total vessels at this berth
        # (proportion of the berth's own traffic that had to queue)
        waiting_at_berth  = (assigned["wait_hours"] > 0).sum()
        queue_depth_ratio = round(waiting_at_berth / vessel_count, 4) if vessel_count > 0 else 0.0

        # Wait pressure: mean wait relative to mean service time
        # (how much of a "service slot" is lost to waiting, per vessel)
        wait_pressure = (
            round(wait_hours_mean / svc_hours_mean, 4)
            if svc_hours_mean > 0 else 0.0
        )

        # Vessel throughput load: vessels per day equivalent
        throughput_load = round(vessel_count / (PLANNING_HORIZON_HOURS / 24), 4)

        # ── Congestion score (0–100, transparent formula) ─────────────────
        # Each factor is normalised to [0, 1] using defensible reference maxima:
        #   utilization_norm  : 1.0 = 100% occupied
        #   queue_depth_norm  : 1.0 = all vessels at this berth had to wait
        #   wait_pressure_norm: 1.0 = mean wait equals mean service time (very bad)
        #   throughput_norm   : 1.0 = 8 vessels in 72 hrs (practical ceiling for 1 berth)
        THROUGHPUT_REF    = 8.0
        utilization_norm  = min(utilization_pct / 100.0, 1.0)
        queue_depth_norm  = min(queue_depth_ratio, 1.0)
        wait_pressure_norm = min(wait_pressure, 1.0)
        throughput_norm   = min(throughput_load / THROUGHPUT_REF, 1.0)

        congestion_score = round(
            100.0 * (
                W_UTILIZATION   * utilization_norm   +
                W_QUEUE_DEPTH   * queue_depth_norm   +
                W_WAIT_PRESSURE * wait_pressure_norm +
                W_VESSEL_COUNT  * throughput_norm
            ), 2
        )

        # Qualitative congestion level
        if congestion_score >= 50:
            level = "HIGH"
        elif congestion_score >= 25:
            level = "MEDIUM"
        elif congestion_score > 0:
            level = "LOW"
        else:
            level = "IDLE"

        berth_rows.append({
            "berth_id":              bid,
            "max_ship_length_m":     berth["max_ship_length_m"],
            "max_draft_m":           berth["max_draft_m"],
            "cranes_available":      berth["cranes_available"],
            "vessel_count":          vessel_count,
            "service_hours_total":   svc_hours_total,
            "utilization_pct":       utilization_pct,
            "wait_hours_total":      wait_hours_total,
            "wait_hours_mean":       round(wait_hours_mean, 2),
            "wait_hours_max":        wait_hours_max,
            "queue_depth_ratio":     queue_depth_ratio,
            "wait_pressure":         wait_pressure,
            "throughput_load":       throughput_load,
            "congestion_score":      congestion_score,
            "congestion_level":      level,
        })

    berth_metrics = pd.DataFrame(berth_rows).sort_values(
        "congestion_score", ascending=False
    ).reset_index(drop=True)

    # ── 3. Vessel flags — identify vessels with significant waiting ───────────
    # "Significant" = wait_hours > 0 (any delay is operationally relevant)
    waiting_vessels = schedule[schedule["wait_hours"] > 0].copy()

    # Enrich with vessel attributes for context
    vessel_detail = vessels[["vessel_id", "priority", "demurrage_cost_per_hour",
                              "cargo_value_usd", "container_count"]].copy()
    vessel_flags = (
        waiting_vessels
        .merge(vessel_detail, on="vessel_id", how="left")
        [[
            "vessel_id", "vessel_name", "berth_id",
            "eta_hours", "start_time", "end_time",
            "wait_hours", "demurrage_cost",
            "priority", "demurrage_cost_per_hour", "cargo_value_usd"
        ]]
        .sort_values("wait_hours", ascending=False)
        .reset_index(drop=True)
    )

    # Severity label
    def _wait_severity(w):
        if w >= 12:   return "CRITICAL"
        elif w >= 6:  return "HIGH"
        elif w >= 3:  return "MODERATE"
        else:         return "LOW"

    vessel_flags["wait_severity"] = vessel_flags["wait_hours"].apply(_wait_severity)

    # ── 4. Hotspot periods — hourly port-wide occupancy ───────────────────────
    # For each hour h in [0, 72), count how many berths are simultaneously active.
    # A berth is active at hour h if any vessel is in service during [start, end).
    hour_records = []
    for h in range(PLANNING_HORIZON_HOURS):
        # Vessels actively being serviced at hour h
        active_mask = (sched_with_svc["start_time"] <= h) & (sched_with_svc["end_time"] > h)
        active_vessels = sched_with_svc[active_mask]

        berths_occupied  = active_vessels["berth_id"].nunique()
        vessels_in_svc   = len(active_vessels)
        # Vessels that have arrived but not yet started (waiting at anchor)
        waiting_mask = (
            (schedule["eta_hours"] <= h) &
            (schedule["start_time"] > h)
        )
        vessels_at_anchor = waiting_mask.sum()

        hour_records.append({
            "hour":               h,
            "berths_occupied":    berths_occupied,
            "vessels_in_service": vessels_in_svc,
            "vessels_at_anchor":  int(vessels_at_anchor),
            "port_load_pct":      round(100.0 * berths_occupied / len(berths), 2),
        })

    hotspot_periods = pd.DataFrame(hour_records)

    # Annotate hours above 60% port load as hotspots
    hotspot_threshold = 60.0
    hotspot_periods["is_hotspot"] = hotspot_periods["port_load_pct"] >= hotspot_threshold

    # ── 5. Bottleneck berth ───────────────────────────────────────────────────
    bottleneck_berth = int(berth_metrics.iloc[0]["berth_id"])

    # ── 6. Metadata — full audit trail ───────────────────────────────────────
    metadata = {
        "method": (
            "Deterministic analytical assessment. "
            "All metrics are computed directly from the 72-hour operational plan "
            "produced by the MIP optimizer. No machine learning is used."
        ),
        "congestion_score_formula": (
            "score = 100 × ("
            f"  {W_UTILIZATION} × utilization_norm"
            f" + {W_QUEUE_DEPTH} × queue_depth_norm"
            f" + {W_WAIT_PRESSURE} × wait_pressure_norm"
            f" + {W_VESSEL_COUNT} × throughput_norm"
            ")"
        ),
        "congestion_score_factors": {
            "utilization_norm":   "service_hours_total / 72  (weight 0.40)",
            "queue_depth_norm":   "vessels_waiting / vessel_count  (weight 0.25)",
            "wait_pressure_norm": "mean_wait / mean_service_time  (weight 0.25)",
            "throughput_norm":    "vessel_count / 8  (weight 0.10)",
        },
        "hotspot_threshold_pct":   hotspot_threshold,
        "planning_horizon_hours":  PLANNING_HORIZON_HOURS,
        "disclaimer": (
            "This is a simulated forward-looking congestion assessment "
            "based on the current 72-hour operational plan. "
            "It is NOT a trained predictive model."
        ),
    }

    return {
        "summary":          summary,
        "berth_metrics":    berth_metrics,
        "vessel_flags":     vessel_flags,
        "hotspot_periods":  hotspot_periods,
        "bottleneck_berth": bottleneck_berth,
        "metadata":         metadata,
    }
