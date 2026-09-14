"""
scenario_engine.py — PortPulse AI: What-If Scenario Engine
===========================================================
Evaluates operational "what-if" scenarios by modifying vessel or berth
inputs and re-running the existing MIP optimizer.

This module does NOT rewrite optimizer logic.
It calls optimizer.optimize_port_schedule() unchanged.
It calls congestion.calculate_congestion_metrics() unchanged.

Supported scenario types
------------------------
BERTH_UNAVAILABLE      – remove one or more berths from the available pool.
ARRIVAL_SURGE          – compress/advance ETAs for a subset of vessels.
PRIORITY_SURGE         – raise the operational priority of selected vessels.
SERVICE_TIME_REDUCTION – reduce service_hours for selected vessels to simulate
                         operational efficiency improvements (faster turnaround).
                         This is NOT crane optimization — crane scheduling is not
                         modelled. It represents any operational intervention that
                         reduces the time a vessel needs at berth.

Priority definition (PortPulse):
  1 = LOW   2 = MEDIUM   3 = HIGH
"""

import pandas as pd
from typing import Any

from optimizer import optimize_port_schedule
from congestion import calculate_congestion_metrics

PLANNING_HORIZON_HOURS = 72

# ── Valid scenario type constants ─────────────────────────────────────────────
BERTH_UNAVAILABLE      = "BERTH_UNAVAILABLE"
ARRIVAL_SURGE          = "ARRIVAL_SURGE"
PRIORITY_SURGE         = "PRIORITY_SURGE"
SERVICE_TIME_REDUCTION = "SERVICE_TIME_REDUCTION"

VALID_SCENARIO_TYPES = {
    BERTH_UNAVAILABLE,
    ARRIVAL_SURGE,
    PRIORITY_SURGE,
    SERVICE_TIME_REDUCTION,
}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _summary_metrics(schedule: pd.DataFrame | None, vessels_df: pd.DataFrame) -> dict:
    """
    Extract scalar metrics from a schedule DataFrame for delta comparison.
    Returns a dict with fixed keys regardless of whether the schedule is None.
    """
    all_vessel_ids = set(vessels_df["vessel_id"].tolist())

    if schedule is None or len(schedule) == 0:
        return {
            "scheduled_vessels":  0,
            "infeasible_vessels": len(all_vessel_ids),
            "total_wait_hours":   None,
            "avg_wait_hours":     None,
            "max_wait_hours":     None,
            "vessels_waiting":    None,
            "total_demurrage":    None,
            "total_berth_op":     None,
            "total_cost":         None,
        }

    sched_ids = set(schedule["vessel_id"].tolist())
    infeasible_count = len(all_vessel_ids - sched_ids)

    return {
        "scheduled_vessels":  len(schedule),
        "infeasible_vessels": infeasible_count,
        "total_wait_hours":   int(schedule["wait_hours"].sum()),
        "avg_wait_hours":     round(schedule["wait_hours"].mean(), 2),
        "max_wait_hours":     int(schedule["wait_hours"].max()),
        "vessels_waiting":    int((schedule["wait_hours"] > 0).sum()),
        "total_demurrage":    int(schedule["demurrage_cost"].sum()),
        "total_berth_op":     int(schedule["berth_operating_cost"].sum()),
        "total_cost":         int(schedule["total_cost"].sum()),
    }


def _per_berth_utilization(schedule: pd.DataFrame | None,
                            berths_df: pd.DataFrame) -> dict:
    """
    Return {berth_id: utilization_pct} for every berth in berths_df.
    Berths with no vessels assigned report 0.0.
    """
    result = {int(bid): 0.0 for bid in berths_df["berth_id"]}
    if schedule is None or len(schedule) == 0:
        return result
    svc = schedule.copy()
    if "service_hours" not in svc.columns:
        svc["service_hours"] = svc["end_time"] - svc["start_time"]
    for bid, grp in svc.groupby("berth_id"):
        result[int(bid)] = round(
            100.0 * grp["service_hours"].sum() / PLANNING_HORIZON_HOURS, 2
        )
    return result


def _identify_infeasible_vessels(scenario_vessels: pd.DataFrame,
                                  scenario_berths: pd.DataFrame,
                                  scenario_schedule: pd.DataFrame | None) -> list[str]:
    """
    Return vessel_ids that appear in scenario_vessels but not in scenario_schedule.
    """
    all_ids = set(scenario_vessels["vessel_id"].tolist())
    if scenario_schedule is None:
        return sorted(all_ids)
    scheduled_ids = set(scenario_schedule["vessel_id"].tolist())
    return sorted(all_ids - scheduled_ids)


def _physical_compatibility(vessel_row: pd.Series,
                              berths_df: pd.DataFrame) -> list[int]:
    """Return list of berth_ids physically compatible with this vessel."""
    compatible = berths_df[
        (berths_df["max_ship_length_m"] >= vessel_row["length_m"]) &
        (berths_df["max_draft_m"]       >= vessel_row["draft_m"])
    ]
    return compatible["berth_id"].tolist()


def _delta(baseline_val, scenario_val) -> Any:
    """Compute scenario_val - baseline_val. Returns None if either is None."""
    if baseline_val is None or scenario_val is None:
        return None
    return scenario_val - baseline_val


def _pct_change(baseline_val, scenario_val) -> Any:
    """Compute percentage change. Returns None if baseline is zero or None."""
    if baseline_val is None or scenario_val is None:
        return None
    if baseline_val == 0:
        return None
    return round(100.0 * (scenario_val - baseline_val) / baseline_val, 2)


# Keys in the metrics dict that are non-scalar and handled separately
_NON_SCALAR_KEYS = {"berth_utilization"}


def _build_deltas(baseline: dict, scenario: dict) -> dict:
    """Build delta and pct_change for every scalar metric key."""
    deltas = {}
    for key in baseline:
        if key in _NON_SCALAR_KEYS:
            continue
        b_val = baseline[key]
        s_val = scenario.get(key)
        deltas[f"{key}_delta"]      = _delta(b_val, s_val)
        deltas[f"{key}_pct_change"] = _pct_change(b_val, s_val)
    # Per-berth utilization deltas (handled as a nested dict)
    if "berth_utilization" in baseline and "berth_utilization" in scenario:
        util_deltas = {}
        for bid, b_util in baseline["berth_utilization"].items():
            s_util = scenario["berth_utilization"].get(bid, 0.0)
            util_deltas[bid] = round(s_util - b_util, 2)
        deltas["berth_utilization_delta"] = util_deltas
    return deltas


# ─────────────────────────────────────────────────────────────────────────────
# Scenario builders — each returns (modified_vessels_df, modified_berths_df,
#                                    description, affected_vessel_ids,
#                                    pre_infeasible_ids)
# ─────────────────────────────────────────────────────────────────────────────

def _build_berth_unavailable(vessels_df: pd.DataFrame,
                               berths_df:  pd.DataFrame,
                               config:     dict):
    """
    Remove berth_ids listed in config['berth_ids'] from the available pool.

    Pre-flight: for each vessel that was exclusively served by the removed
    berths in the baseline, check whether any remaining berth is physically
    compatible.  Vessels with no compatible remaining berth are pre-marked
    infeasible and excluded from the optimizer call — this prevents the
    optimizer returning None on an otherwise solvable subset.
    """
    unavailable = config.get("berth_ids", [])
    if not unavailable:
        raise ValueError("BERTH_UNAVAILABLE scenario requires 'berth_ids' in config.")

    reduced_berths = berths_df[~berths_df["berth_id"].isin(unavailable)].copy()
    if len(reduced_berths) == 0:
        raise ValueError("All berths removed — no feasible berths remain.")

    # Identify vessels that have no compatible berth in the reduced set
    pre_infeasible = []
    feasible_vessels = []
    for _, v in vessels_df.iterrows():
        compat = _physical_compatibility(v, reduced_berths)
        if not compat:
            pre_infeasible.append(v["vessel_id"])
        else:
            feasible_vessels.append(v)

    feasible_df = pd.DataFrame(feasible_vessels).reset_index(drop=True) \
                  if feasible_vessels else pd.DataFrame(columns=vessels_df.columns)

    removed_str = ", ".join(str(b) for b in unavailable)
    infeas_str  = ", ".join(pre_infeasible) if pre_infeasible else "none"
    description = (
        f"Berth(s) {removed_str} marked unavailable. "
        f"Re-optimised with {len(reduced_berths)} berth(s) and "
        f"{len(feasible_df)} vessels. "
        f"Structurally infeasible vessels (no compatible remaining berth): "
        f"{infeas_str}."
    )
    return feasible_df, reduced_berths, description, [], pre_infeasible


def _build_arrival_surge(vessels_df: pd.DataFrame,
                          berths_df:  pd.DataFrame,
                          config:     dict):
    """
    Advance (reduce) ETAs for a subset of vessels to simulate an arrival surge.

    config keys:
      vessel_ids        – list of vessel_ids to affect, OR
      fraction          – float (0–1): apply to this fraction of vessels
                          sorted by eta_hours ascending (earliest arrivals first)
      compression_hours – int: reduce each affected vessel's ETA by this many hours
                          (floor at 0, default 2)

    Deterministic: no randomness.  When fraction is used, vessels are sorted
    by eta_hours then vessel_id for a stable, reproducible selection.
    """
    compression = int(config.get("compression_hours", 2))
    modified    = vessels_df.copy()

    if "vessel_ids" in config:
        target_ids = set(config["vessel_ids"])
    elif "fraction" in config:
        frac = float(config["fraction"])
        if not (0.0 < frac <= 1.0):
            raise ValueError("fraction must be in (0, 1]")
        n = max(1, round(len(vessels_df) * frac))
        # Stable sort: eta_hours ascending, then vessel_id for tie-breaking
        sorted_vessels = vessels_df.sort_values(
            ["eta_hours", "vessel_id"]
        )
        target_ids = set(sorted_vessels.head(n)["vessel_id"].tolist())
    else:
        raise ValueError(
            "ARRIVAL_SURGE requires 'vessel_ids' or 'fraction' in config."
        )

    modified["eta_hours"] = modified.apply(
        lambda row: max(0, int(row["eta_hours"]) - compression)
        if row["vessel_id"] in target_ids
        else int(row["eta_hours"]),
        axis=1,
    )

    affected = sorted(target_ids & set(vessels_df["vessel_id"].tolist()))
    target_str = ", ".join(affected)
    description = (
        f"ARRIVAL_SURGE: ETA compressed by {compression} hour(s) for "
        f"{len(affected)} vessel(s): {target_str}. "
        f"Deterministic selection — no randomness used."
    )
    return modified, berths_df.copy(), description, affected, []


def _build_priority_surge(vessels_df: pd.DataFrame,
                            berths_df:  pd.DataFrame,
                            config:     dict):
    """
    Raise the operational priority of selected vessels to config['new_priority']
    (default 3 = HIGH).

    config keys:
      vessel_ids   – list of vessel_ids to upgrade
      new_priority – int 1–3 (default 3)

    Priority meaning: 1=LOW, 2=MEDIUM, 3=HIGH.
    """
    new_priority = int(config.get("new_priority", 3))
    if new_priority not in (1, 2, 3):
        raise ValueError("new_priority must be 1, 2, or 3 (1=LOW, 2=MED, 3=HIGH).")

    target_ids = set(config.get("vessel_ids", []))
    if not target_ids:
        raise ValueError("PRIORITY_SURGE requires 'vessel_ids' in config.")

    modified = vessels_df.copy()
    changed  = []
    for idx, row in modified.iterrows():
        if row["vessel_id"] in target_ids:
            old = row["priority"]
            modified.at[idx, "priority"] = new_priority
            changed.append(
                f"{row['vessel_id']} ({old}→{new_priority})"
            )

    affected = sorted(target_ids & set(vessels_df["vessel_id"].tolist()))
    label    = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
    description = (
        f"PRIORITY_SURGE: priority raised to {new_priority} "
        f"({label[new_priority]}) for {len(affected)} vessel(s). "
        f"Changes: {', '.join(changed)}. "
        f"Optimizer re-weighted demurrage penalties accordingly."
    )
    return modified, berths_df.copy(), description, affected, []


def _build_service_time_reduction(vessels_df: pd.DataFrame,
                                   berths_df:  pd.DataFrame,
                                   config:     dict):
    """
    Reduce service_hours for selected vessels to simulate an operational
    efficiency intervention (faster loading/unloading turnaround).

    This is NOT crane optimization.  Crane scheduling is not modelled.
    The scenario represents any intervention that shortens berth occupancy —
    e.g. additional labour, pre-staged cargo, improved equipment utilisation.

    config keys:
      vessel_ids    – list of vessel_ids to affect (required)
      reduction_pct – int/float >0 and <=100: percentage reduction in
                      service_hours (default 20)

    Formula:
      new_service_hours = max(1, floor(original * (1 - reduction_pct / 100)))

    Deterministic: identical config always produces the same result.
    All other vessel attributes are preserved unchanged.
    """
    import math

    target_ids   = set(config.get("vessel_ids", []))
    if not target_ids:
        raise ValueError(
            "SERVICE_TIME_REDUCTION requires 'vessel_ids' in config."
        )

    # Validate that every supplied vessel_id actually exists
    known_ids = set(vessels_df["vessel_id"].tolist())
    unknown   = target_ids - known_ids
    if unknown:
        raise ValueError(
            f"SERVICE_TIME_REDUCTION: unknown vessel_id(s): {sorted(unknown)}"
        )

    reduction_pct = float(config.get("reduction_pct", 20))
    if not (0 < reduction_pct <= 100):
        raise ValueError(
            "reduction_pct must be > 0 and <= 100 "
            f"(got {reduction_pct})."
        )

    modified  = vessels_df.copy()
    changes   = []
    for idx, row in modified.iterrows():
        if row["vessel_id"] in target_ids:
            original = int(row["service_hours"])
            reduced  = max(1, math.floor(original * (1 - reduction_pct / 100)))
            modified.at[idx, "service_hours"] = reduced
            changes.append(
                f"{row['vessel_id']} ({original}h→{reduced}h)"
            )

    affected = sorted(target_ids)
    description = (
        f"SERVICE_TIME_REDUCTION: service_hours reduced by {reduction_pct:.0f}% "
        f"(floor, min 1h) for {len(affected)} vessel(s). "
        f"Changes: {', '.join(changes)}. "
        f"This simulates an operational efficiency intervention "
        f"(faster turnaround at berth). "
        f"NOT crane optimization — crane scheduling is not modelled."
    )
    return modified, berths_df.copy(), description, affected, []


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def run_scenario(
    scenario_type:   str,
    vessels_df:      pd.DataFrame,
    berths_df:       pd.DataFrame,
    scenario_config: dict,
) -> dict:
    """
    Evaluate a what-if scenario by modifying inputs and re-running the optimizer.

    Parameters
    ----------
    scenario_type   : one of BERTH_UNAVAILABLE, ARRIVAL_SURGE, PRIORITY_SURGE
    vessels_df      : original vessels DataFrame (not mutated)
    berths_df       : original berths DataFrame (not mutated)
    scenario_config : scenario-specific parameters (see individual builders)

    Returns
    -------
    dict with keys:
      scenario_type        str
      scenario_name        str  (human-readable)
      scenario_description str
      feasibility_status   str  FULL / PARTIAL / INFEASIBLE
      baseline_metrics     dict
      scenario_metrics     dict
      metric_deltas        dict
      baseline_schedule    DataFrame | None
      scenario_schedule    DataFrame | None
      vessels_affected     list[str]
      vessels_infeasible   list[str]  (structurally incompatible OR dropped)
      bottleneck_berth_baseline  int | None
      bottleneck_berth_scenario  int | None
      scenario_berths      DataFrame  (berths used in scenario)
      config               dict       (echo of scenario_config for auditability)
    """

    if scenario_type not in VALID_SCENARIO_TYPES:
        raise ValueError(
            f"Unknown scenario_type '{scenario_type}'. "
            f"Valid types: {sorted(VALID_SCENARIO_TYPES)}"
        )

    # ── Defensive copies of caller data ──────────────────────────────────────
    v_base = vessels_df.copy()
    b_base = berths_df.copy()

    # ── Baseline: run optimizer on original data ──────────────────────────────
    baseline_schedule = optimize_port_schedule(v_base, b_base)

    base_metrics = _summary_metrics(baseline_schedule, v_base)
    base_metrics["berth_utilization"] = _per_berth_utilization(
        baseline_schedule, b_base
    )

    # Baseline bottleneck
    base_bottleneck = None
    if baseline_schedule is not None:
        base_cong = calculate_congestion_metrics(v_base, b_base, baseline_schedule)
        base_bottleneck = base_cong["bottleneck_berth"]

    # ── Build scenario inputs ─────────────────────────────────────────────────
    scenario_names = {
        BERTH_UNAVAILABLE:      "Berth Unavailable",
        ARRIVAL_SURGE:          "Arrival Surge",
        PRIORITY_SURGE:         "Priority Surge",
        SERVICE_TIME_REDUCTION: "Service Time Reduction",
    }

    builders = {
        BERTH_UNAVAILABLE:      _build_berth_unavailable,
        ARRIVAL_SURGE:          _build_arrival_surge,
        PRIORITY_SURGE:         _build_priority_surge,
        SERVICE_TIME_REDUCTION: _build_service_time_reduction,
    }

    (sc_vessels, sc_berths,
     description, affected_ids,
     pre_infeasible_ids) = builders[scenario_type](v_base, b_base, scenario_config)

    # ── Run scenario optimizer ────────────────────────────────────────────────
    if len(sc_vessels) == 0:
        # All vessels are pre-infeasible
        sc_schedule = None
    else:
        sc_schedule = optimize_port_schedule(sc_vessels, sc_berths)

    # ── Collect post-run infeasible vessels ───────────────────────────────────
    post_infeasible_ids = _identify_infeasible_vessels(
        sc_vessels, sc_berths, sc_schedule
    )
    all_infeasible = sorted(set(pre_infeasible_ids + post_infeasible_ids))

    # ── Scenario metrics ──────────────────────────────────────────────────────
    # Build a full-fleet vessels_df for metric reporting (includes pre-infeasible)
    sc_metrics = _summary_metrics(sc_schedule, v_base)
    sc_metrics["berth_utilization"] = _per_berth_utilization(
        sc_schedule, sc_berths
    )

    # ── Scenario bottleneck ───────────────────────────────────────────────────
    sc_bottleneck = None
    if sc_schedule is not None and len(sc_schedule) > 0:
        sc_cong = calculate_congestion_metrics(sc_vessels, sc_berths, sc_schedule)
        sc_bottleneck = sc_cong["bottleneck_berth"]

    # ── Deltas ────────────────────────────────────────────────────────────────
    deltas = _build_deltas(base_metrics, sc_metrics)

    # ── Feasibility status ────────────────────────────────────────────────────
    if sc_schedule is None:
        feasibility = "INFEASIBLE"
    elif all_infeasible:
        feasibility = "PARTIAL"
    else:
        feasibility = "FULL"

    return {
        "scenario_type":               scenario_type,
        "scenario_name":               scenario_names[scenario_type],
        "scenario_description":        description,
        "feasibility_status":          feasibility,
        "baseline_metrics":            base_metrics,
        "scenario_metrics":            sc_metrics,
        "metric_deltas":               deltas,
        "baseline_schedule":           baseline_schedule,
        "scenario_schedule":           sc_schedule,
        "vessels_affected":            affected_ids,
        "vessels_infeasible":          all_infeasible,
        "bottleneck_berth_baseline":   base_bottleneck,
        "bottleneck_berth_scenario":   sc_bottleneck,
        "scenario_berths":             sc_berths,
        "config":                      dict(scenario_config),
    }
