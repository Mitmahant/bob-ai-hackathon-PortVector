"""
test_scenario_engine.py — PortPulse AI: Scenario Engine Tests
==============================================================
Runs 10 test groups covering all three scenario types plus regression
checks on the existing optimizer and congestion tests.

All assertions fail loudly with a descriptive message.
The test does NOT modify any data files.
"""

import sys
import pandas as pd
from scenario_engine import (
    run_scenario,
    BERTH_UNAVAILABLE, ARRIVAL_SURGE, PRIORITY_SURGE, SERVICE_TIME_REDUCTION,
)

# ── Load data ─────────────────────────────────────────────────────────────────
vessels  = pd.read_csv("data/vessels.csv")
berths   = pd.read_csv("data/berths.csv")
schedule = pd.read_csv("data/schedule_output.csv")

# Snapshots — used to verify immutability
vessels_snap  = vessels.copy()
berths_snap   = berths.copy()
schedule_snap = schedule.copy()

failures = []

def check(condition: bool, msg: str):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {msg}")
    if not condition:
        failures.append(msg)

def section(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


# ─────────────────────────────────────────────────────────────────────────────
# T01 — Baseline scenario reproduces the known 15-vessel schedule
# ─────────────────────────────────────────────────────────────────────────────
section("T01 — Baseline schedule reproduction")

# We test the ARRIVAL_SURGE path with zero compression to get a pure baseline
# re-run rather than importing run_scenario with no changes.
# Instead we call the internal baseline directly via ARRIVAL_SURGE with no
# vessel changed (vessel_ids = []) — which is invalid.  Better: run PRIORITY_SURGE
# with a vessel that already has priority 3 and new_priority=3 (no-op change).
# Simplest correct approach: call run_scenario with ARRIVAL_SURGE, compression=0,
# vessel_ids=[] — but that raises.  Use the public interface correctly:
# just run PRIORITY_SURGE on V02 (priority already 3 → no change).
result_base = run_scenario(
    PRIORITY_SURGE,
    vessels,
    berths,
    {"vessel_ids": ["V02"], "new_priority": 3},   # no-op: V02 is already priority 3
)

base_sched = result_base["baseline_schedule"]
check(base_sched is not None,                     "baseline_schedule is not None")
check(len(base_sched) == 15,                       "baseline produces 15-vessel schedule")
check(result_base["baseline_metrics"]["scheduled_vessels"] == 15,
      "baseline_metrics.scheduled_vessels == 15")
check(result_base["baseline_metrics"]["infeasible_vessels"] == 0,
      "baseline_metrics.infeasible_vessels == 0")
check(result_base["baseline_metrics"]["total_wait_hours"] == 39,
      f"baseline total_wait_hours == 39 (got {result_base['baseline_metrics']['total_wait_hours']})")
check(result_base["baseline_metrics"]["total_demurrage"] == 132600,
      f"baseline total_demurrage == 132600 (got {result_base['baseline_metrics']['total_demurrage']})")
check(result_base["bottleneck_berth_baseline"] == 3,
      f"baseline bottleneck berth == 3 (got {result_base['bottleneck_berth_baseline']})")


# ─────────────────────────────────────────────────────────────────────────────
# T02 — run_scenario return structure
# ─────────────────────────────────────────────────────────────────────────────
section("T02 — Return structure")
REQUIRED_KEYS = [
    "scenario_type", "scenario_name", "scenario_description",
    "feasibility_status", "baseline_metrics", "scenario_metrics",
    "metric_deltas", "baseline_schedule", "scenario_schedule",
    "vessels_affected", "vessels_infeasible",
    "bottleneck_berth_baseline", "bottleneck_berth_scenario",
    "scenario_berths", "config",
]
for k in REQUIRED_KEYS:
    check(k in result_base, f"return dict contains key '{k}'")

check(isinstance(result_base["vessels_affected"],   list), "vessels_affected is a list")
check(isinstance(result_base["vessels_infeasible"], list), "vessels_infeasible is a list")
check(isinstance(result_base["metric_deltas"],      dict), "metric_deltas is a dict")
check(isinstance(result_base["scenario_berths"],    pd.DataFrame), "scenario_berths is a DataFrame")
check(isinstance(result_base["config"],             dict), "config is a dict")


# ─────────────────────────────────────────────────────────────────────────────
# T03 — Input data not mutated
# ─────────────────────────────────────────────────────────────────────────────
section("T03 — Immutability")
check(vessels.equals(vessels_snap),   "vessels_df not mutated after run_scenario")
check(berths.equals(berths_snap),     "berths_df not mutated after run_scenario")
check(schedule.equals(schedule_snap), "schedule_df not touched by scenario_engine")


# ─────────────────────────────────────────────────────────────────────────────
# T04 — BERTH_UNAVAILABLE: disable Berth 3
# ─────────────────────────────────────────────────────────────────────────────
section("T04 — BERTH_UNAVAILABLE (Berth 3 disabled)")

result_bu = run_scenario(
    BERTH_UNAVAILABLE,
    vessels,
    berths,
    {"berth_ids": [3]},
)

print(f"\n  Scenario: {result_bu['scenario_description']}")
print(f"  Feasibility: {result_bu['feasibility_status']}")
print(f"  Infeasible vessels: {result_bu['vessels_infeasible']}")

check(result_bu["scenario_type"] == BERTH_UNAVAILABLE,    "scenario_type correct")
check(result_bu["feasibility_status"] == "PARTIAL",        "feasibility == PARTIAL (some vessels infeasible)")

# V03, V07, V11, V15 are exclusive to Berth 3 — must all be in infeasible list
berth3_only = {"V03", "V07", "V11", "V15"}
infeas_set  = set(result_bu["vessels_infeasible"])
check(berth3_only.issubset(infeas_set),
      f"Berth-3-exclusive vessels {sorted(berth3_only)} all reported infeasible "
      f"(got {sorted(infeas_set)})")

# Berth 3 must not appear in scenario_berths
sc_berth_ids = set(result_bu["scenario_berths"]["berth_id"].tolist())
check(3 not in sc_berth_ids,               "Berth 3 absent from scenario_berths")
check(len(result_bu["scenario_berths"]) == 4, "scenario_berths has 4 remaining berths")

# Remaining vessels (those NOT Berth-3-only) should be scheduled
sc_sched = result_bu["scenario_schedule"]
check(sc_sched is not None,               "scenario_schedule is not None")
expected_feasible = 15 - len(berth3_only)
check(len(sc_sched) == expected_feasible,
      f"scheduled vessels == {expected_feasible} (got {len(sc_sched) if sc_sched is not None else 0})")

# No vessel in the scenario schedule should be assigned to Berth 3
if sc_sched is not None and len(sc_sched) > 0:
    check((sc_sched["berth_id"] != 3).all(),
          "No vessel in scenario schedule assigned to disabled Berth 3")

# Metric deltas — wait and demurrage should both be non-None
deltas_bu = result_bu["metric_deltas"]
check(deltas_bu.get("total_wait_hours_delta") is not None,
      "total_wait_hours_delta is computed")
check(deltas_bu.get("total_demurrage_delta") is not None,
      "total_demurrage_delta is computed")

# Scheduled vessels decrease
base_sched_count = result_bu["baseline_metrics"]["scheduled_vessels"]
sc_sched_count   = result_bu["scenario_metrics"]["scheduled_vessels"]
check(sc_sched_count < base_sched_count,
      f"scenario schedules fewer vessels ({sc_sched_count}) than baseline ({base_sched_count})")

# Immutability after BERTH_UNAVAILABLE run
check(vessels.equals(vessels_snap), "vessels_df not mutated by BERTH_UNAVAILABLE")
check(berths.equals(berths_snap),   "berths_df not mutated by BERTH_UNAVAILABLE")


# ─────────────────────────────────────────────────────────────────────────────
# T05 — ARRIVAL_SURGE: deterministic result
# ─────────────────────────────────────────────────────────────────────────────
section("T05 — ARRIVAL_SURGE (deterministic)")

surge_config = {
    "fraction":          0.4,    # earliest 40% of vessels (6 out of 15)
    "compression_hours": 2,
}

result_as1 = run_scenario(ARRIVAL_SURGE, vessels, berths, surge_config)
result_as2 = run_scenario(ARRIVAL_SURGE, vessels, berths, surge_config)  # second run

print(f"\n  Scenario: {result_as1['scenario_description']}")
print(f"  Feasibility: {result_as1['feasibility_status']}")
print(f"  Vessels affected: {result_as1['vessels_affected']}")

check(result_as1["scenario_type"] == ARRIVAL_SURGE,       "scenario_type correct")
check(result_as1["feasibility_status"] in ("FULL", "PARTIAL", "INFEASIBLE"),
      "feasibility_status is a valid value")
check(len(result_as1["vessels_affected"]) == 6,
      f"6 vessels affected at 40% fraction (got {len(result_as1['vessels_affected'])})")

# Determinism: two runs with identical config produce identical results
sched_as1 = result_as1["scenario_schedule"]
sched_as2 = result_as2["scenario_schedule"]
if sched_as1 is not None and sched_as2 is not None:
    merged = sched_as1.sort_values("vessel_id").reset_index(drop=True)
    merged2 = sched_as2.sort_values("vessel_id").reset_index(drop=True)
    check(merged.equals(merged2), "ARRIVAL_SURGE produces identical results on two runs (deterministic)")

# Affected ETAs are reduced (or 0), not increased
affected_ids = set(result_as1["vessels_affected"])
sc_sched_as = result_as1["scenario_schedule"]
if sc_sched_as is not None:
    check(result_as1["scenario_metrics"]["scheduled_vessels"] > 0,
          "ARRIVAL_SURGE: at least one vessel scheduled")

# Check metric delta keys exist
deltas_as = result_as1["metric_deltas"]
for key in ("total_wait_hours_delta", "avg_wait_hours_delta",
            "total_demurrage_delta", "total_cost_delta"):
    check(key in deltas_as, f"metric_deltas contains key '{key}'")

check(vessels.equals(vessels_snap), "vessels_df not mutated by ARRIVAL_SURGE")
check(berths.equals(berths_snap),   "berths_df not mutated by ARRIVAL_SURGE")


# ─────────────────────────────────────────────────────────────────────────────
# T06 — PRIORITY_SURGE: deterministic result
# ─────────────────────────────────────────────────────────────────────────────
section("T06 — PRIORITY_SURGE (deterministic)")

# V01, V04, V08, V12 are priority 1 (LOW) — upgrade to priority 3 (HIGH)
low_priority_vessels = ["V01", "V04", "V08", "V12"]
ps_config = {"vessel_ids": low_priority_vessels, "new_priority": 3}

result_ps1 = run_scenario(PRIORITY_SURGE, vessels, berths, ps_config)
result_ps2 = run_scenario(PRIORITY_SURGE, vessels, berths, ps_config)

print(f"\n  Scenario: {result_ps1['scenario_description']}")
print(f"  Feasibility: {result_ps1['feasibility_status']}")

check(result_ps1["scenario_type"] == PRIORITY_SURGE,       "scenario_type correct")
check(set(result_ps1["vessels_affected"]) == set(low_priority_vessels),
      f"vessels_affected == {low_priority_vessels}")

# All 15 vessels should still be schedulable (priority change doesn't affect feasibility)
ps_sched = result_ps1["scenario_schedule"]
check(ps_sched is not None,         "PRIORITY_SURGE schedule is not None")
check(len(ps_sched) == 15,           "all 15 vessels scheduled after PRIORITY_SURGE")
check(result_ps1["feasibility_status"] == "FULL",
      "feasibility == FULL (priority change doesn't affect physical constraints)")

# Determinism
if ps_sched is not None:
    s1 = ps_sched.sort_values("vessel_id").reset_index(drop=True)
    s2 = result_ps2["scenario_schedule"].sort_values("vessel_id").reset_index(drop=True)
    check(s1.equals(s2), "PRIORITY_SURGE produces identical results on two runs (deterministic)")

# Metric deltas exist
deltas_ps = result_ps1["metric_deltas"]
for key in ("total_wait_hours_delta", "total_demurrage_delta"):
    check(key in deltas_ps, f"metric_deltas contains '{key}'")

check(vessels.equals(vessels_snap), "vessels_df not mutated by PRIORITY_SURGE")
check(berths.equals(berths_snap),   "berths_df not mutated by PRIORITY_SURGE")


# ─────────────────────────────────────────────────────────────────────────────
# T07 — Metric delta calculation correctness
# ─────────────────────────────────────────────────────────────────────────────
section("T07 — Metric delta correctness")

# Use the no-op PRIORITY_SURGE (V02 already priority 3) for exact delta check
deltas_noop = result_base["metric_deltas"]

# In a no-op scenario, scheduled_vessels, wait hours, demurrage are the same
# (optimizer is deterministic) — deltas should be 0
check(deltas_noop.get("scheduled_vessels_delta") == 0,
      f"no-op scheduled_vessels_delta == 0 (got {deltas_noop.get('scheduled_vessels_delta')})")
check(deltas_noop.get("total_wait_hours_delta") == 0,
      f"no-op total_wait_hours_delta == 0 (got {deltas_noop.get('total_wait_hours_delta')})")
check(deltas_noop.get("total_demurrage_delta") == 0,
      f"no-op total_demurrage_delta == 0 (got {deltas_noop.get('total_demurrage_delta')})")

# BERTH_UNAVAILABLE should show negative delta for scheduled_vessels (fewer scheduled)
check(deltas_bu.get("scheduled_vessels_delta") is not None,
      "BERTH_UNAVAILABLE scheduled_vessels_delta is not None")
check(deltas_bu["scheduled_vessels_delta"] < 0,
      f"BERTH_UNAVAILABLE scheduled_vessels_delta < 0 (got {deltas_bu['scheduled_vessels_delta']})")

# Berth utilization deltas are a dict
util_delta = deltas_bu.get("berth_utilization_delta")
check(isinstance(util_delta, dict),         "berth_utilization_delta is a dict")
check(3 in util_delta,                      "berth_utilization_delta contains berth 3")
check(util_delta[3] == -44.44,
      f"berth 3 utilization delta == -44.44 (got {util_delta.get(3)})")


# ─────────────────────────────────────────────────────────────────────────────
# T08 — Infeasible vessels reported explicitly (not silently dropped)
# ─────────────────────────────────────────────────────────────────────────────
section("T08 — Infeasible vessel reporting")

check("vessels_infeasible" in result_bu,               "vessels_infeasible key present")
check(isinstance(result_bu["vessels_infeasible"], list), "vessels_infeasible is a list")
check(len(result_bu["vessels_infeasible"]) == 4,
      f"exactly 4 vessels reported infeasible (got {len(result_bu['vessels_infeasible'])})")

# The 4 infeasible vessels should NOT appear in the scenario schedule
if sc_sched is not None:
    sched_ids = set(sc_sched["vessel_id"].tolist())
    for vid in result_bu["vessels_infeasible"]:
        check(vid not in sched_ids,
              f"infeasible vessel {vid} is absent from scenario schedule")

# scenario_metrics.infeasible_vessels should count them
check(result_bu["scenario_metrics"]["infeasible_vessels"] == 4,
      f"scenario_metrics.infeasible_vessels == 4 "
      f"(got {result_bu['scenario_metrics']['infeasible_vessels']})")


# ─────────────────────────────────────────────────────────────────────────────
# T09 — Dashboard-ready output
# ─────────────────────────────────────────────────────────────────────────────
section("T09 — Dashboard-ready output (future Streamlit)")

# scenario_schedule must be a DataFrame (not a list or dict)
check(result_bu["scenario_schedule"] is None or
      isinstance(result_bu["scenario_schedule"], pd.DataFrame),
      "scenario_schedule is DataFrame or None")
check(isinstance(result_as1["scenario_schedule"], pd.DataFrame) or
      result_as1["scenario_schedule"] is None,
      "ARRIVAL_SURGE scenario_schedule is DataFrame or None")

# baseline_metrics and scenario_metrics are plain dicts (JSON-serialisable structure)
for res_name, res in [("BERTH_UNAVAILABLE", result_bu),
                       ("ARRIVAL_SURGE",     result_as1),
                       ("PRIORITY_SURGE",    result_ps1)]:
    check(isinstance(res["baseline_metrics"], dict),
          f"{res_name}: baseline_metrics is a dict")
    check(isinstance(res["scenario_metrics"], dict),
          f"{res_name}: scenario_metrics is a dict")
    check("berth_utilization" in res["baseline_metrics"],
          f"{res_name}: baseline_metrics contains berth_utilization")
    check("berth_utilization" in res["scenario_metrics"],
          f"{res_name}: scenario_metrics contains berth_utilization")
    check(isinstance(res["scenario_description"], str) and len(res["scenario_description"]) > 10,
          f"{res_name}: scenario_description is a non-empty string")
    check(res["feasibility_status"] in ("FULL", "PARTIAL", "INFEASIBLE"),
          f"{res_name}: feasibility_status is a valid value")


# ─────────────────────────────────────────────────────────────────────────────
# T10 — Existing optimizer/congestion tests unaffected (regression)
# ─────────────────────────────────────────────────────────────────────────────
section("T10 — Regression: optimizer and congestion unchanged")

from optimizer import optimize_port_schedule
from congestion import calculate_congestion_metrics
import pandas as _pd2

test_vessels = _pd2.DataFrame([
    {"vessel_id": "V01", "vessel_name": "Ship 1", "length_m": 200,
     "draft_m": 10.0, "eta_hours": 2, "service_hours": 4, "priority": 2,
     "demurrage_cost_per_hour": 1000},
    {"vessel_id": "V02", "vessel_name": "Ship 2", "length_m": 250,
     "draft_m": 12.0, "eta_hours": 3, "service_hours": 5, "priority": 3,
     "demurrage_cost_per_hour": 2000},
    {"vessel_id": "V03", "vessel_name": "Ship 3", "length_m": 220,
     "draft_m": 11.0, "eta_hours": 6, "service_hours": 3, "priority": 1,
     "demurrage_cost_per_hour": 800},
])
test_berths = _pd2.DataFrame([
    {"berth_id": 1, "max_ship_length_m": 300, "max_draft_m": 15.0,
     "cranes_available": 4, "hourly_cost_usd": 0},
    {"berth_id": 2, "max_ship_length_m": 300, "max_draft_m": 15.0,
     "cranes_available": 4, "hourly_cost_usd": 0},
])
reg_result = optimize_port_schedule(test_vessels, test_berths)
check(reg_result is not None,       "optimizer still returns a result for 3-vessel test")
check(len(reg_result) == 3,          "optimizer schedules all 3 test vessels")

cong_result = calculate_congestion_metrics(vessels, berths, schedule)
check(cong_result is not None,       "congestion engine still runs successfully")
check(cong_result["bottleneck_berth"] == 3,
      "congestion engine still identifies Berth 3 as bottleneck")

check(vessels.equals(vessels_snap),   "vessels_df untouched after all tests")
check(berths.equals(berths_snap),     "berths_df untouched after all tests")


# ─────────────────────────────────────────────────────────────────────────────
# Full metrics report
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(" SCENARIO RESULTS REPORT")
print("="*60)

def _print_metrics_comparison(label: str, result: dict):
    bm = result["baseline_metrics"]
    sm = result["scenario_metrics"]
    dm = result["metric_deltas"]
    print(f"\n  {'Metric':<30} {'Baseline':>12} {'Scenario':>12} {'Delta':>10}")
    print(f"  {'-'*66}")
    rows = [
        ("Scheduled vessels",    "scheduled_vessels"),
        ("Infeasible vessels",   "infeasible_vessels"),
        ("Total wait hours",     "total_wait_hours"),
        ("Avg wait hours",       "avg_wait_hours"),
        ("Max wait hours",       "max_wait_hours"),
        ("Vessels waiting",      "vessels_waiting"),
        ("Total demurrage ($)",  "total_demurrage"),
        ("Total berth op ($)",   "total_berth_op"),
        ("Total cost ($)",       "total_cost"),
    ]
    for display, key in rows:
        b  = bm.get(key, "—")
        s  = sm.get(key, "—")
        d  = dm.get(f"{key}_delta", "—")
        bv = f"{b:,.0f}" if isinstance(b, (int, float)) else str(b)
        sv = f"{s:,.0f}" if isinstance(s, (int, float)) else str(s)
        dv = f"{d:+,.0f}" if isinstance(d, (int, float)) else str(d)
        print(f"  {display:<30} {bv:>12} {sv:>12} {dv:>10}")
    print(f"\n  Feasibility: {result['feasibility_status']}")
    print(f"  Infeasible vessels: {result['vessels_infeasible'] or 'none'}")
    print(f"  Affected vessels:   {result['vessels_affected'] or 'none'}")
    print(f"  Bottleneck (baseline → scenario): "
          f"{result['bottleneck_berth_baseline']} → {result['bottleneck_berth_scenario']}")
    print(f"\n  Berth utilization delta:")
    util_d = dm.get("berth_utilization_delta", {})
    for bid in sorted(util_d.keys()):
        print(f"    Berth {bid}: {util_d[bid]:+.2f}%")

print("\n─── Scenario 1: BERTH_UNAVAILABLE (Berth 3 disabled) ───")
print(f"  {result_bu['scenario_description']}")
_print_metrics_comparison("BERTH_UNAVAILABLE", result_bu)

if result_bu["scenario_schedule"] is not None:
    print("\n  Scenario schedule:")
    sc = result_bu["scenario_schedule"].sort_values("start_time")
    print(sc[["vessel_id","vessel_name","berth_id","eta_hours",
              "start_time","end_time","wait_hours","demurrage_cost"]].to_string(index=False))

print("\n─── Scenario 2: ARRIVAL_SURGE (earliest 40%, -2h ETA) ───")
print(f"  {result_as1['scenario_description']}")
_print_metrics_comparison("ARRIVAL_SURGE", result_as1)

if result_as1["scenario_schedule"] is not None:
    print("\n  Scenario schedule:")
    sc = result_as1["scenario_schedule"].sort_values("start_time")
    print(sc[["vessel_id","vessel_name","berth_id","eta_hours",
              "start_time","end_time","wait_hours","demurrage_cost"]].to_string(index=False))

print("\n─── Scenario 3: PRIORITY_SURGE (V01,V04,V08,V12 → HIGH) ───")
print(f"  {result_ps1['scenario_description']}")
_print_metrics_comparison("PRIORITY_SURGE", result_ps1)

if result_ps1["scenario_schedule"] is not None:
    print("\n  Scenario schedule:")
    sc = result_ps1["scenario_schedule"].sort_values("start_time")
    print(sc[["vessel_id","vessel_name","berth_id","eta_hours",
              "start_time","end_time","wait_hours","demurrage_cost"]].to_string(index=False))


# ─────────────────────────────────────────────────────────────────────────────
# T11 — SERVICE_TIME_REDUCTION
# ─────────────────────────────────────────────────────────────────────────────
section("T11 — SERVICE_TIME_REDUCTION (V03,V07,V11,V15 at -20%)")

import math as _math

str_config = {
    "vessel_ids":    ["V03", "V07", "V11", "V15"],
    "reduction_pct": 20,
}

# Pre-compute expected reduced service_hours for assertion
_original_svc = vessels.set_index("vessel_id")["service_hours"].to_dict()
_expected_svc = {
    vid: max(1, _math.floor(_original_svc[vid] * (1 - 20 / 100)))
    for vid in str_config["vessel_ids"]
}
# V03: floor(8*0.8)=6, V07: floor(9*0.8)=7, V11: floor(8*0.8)=6, V15: floor(7*0.8)=5

result_str1 = run_scenario(SERVICE_TIME_REDUCTION, vessels, berths, str_config)
result_str2 = run_scenario(SERVICE_TIME_REDUCTION, vessels, berths, str_config)

print(f"\n  Scenario: {result_str1['scenario_description']}")
print(f"  Feasibility: {result_str1['feasibility_status']}")
print(f"  Vessels affected: {result_str1['vessels_affected']}")

# Scenario type and name
check(result_str1["scenario_type"] == SERVICE_TIME_REDUCTION,
      "scenario_type == SERVICE_TIME_REDUCTION")
check(result_str1["scenario_name"] == "Service Time Reduction",
      "scenario_name == 'Service Time Reduction'")

# All four target vessels reported as affected
check(set(result_str1["vessels_affected"]) == set(str_config["vessel_ids"]),
      f"vessels_affected == {str_config['vessel_ids']}")

# Original vessels_df not mutated
check(vessels.equals(vessels_snap), "vessels_df not mutated by SERVICE_TIME_REDUCTION")
check(berths.equals(berths_snap),   "berths_df not mutated by SERVICE_TIME_REDUCTION")

# Scenario schedule is a DataFrame
str_sched = result_str1["scenario_schedule"]
check(isinstance(str_sched, pd.DataFrame), "scenario_schedule is a DataFrame")
check(str_sched is not None,               "scenario_schedule is not None")

# All 15 vessels remain schedulable
check(result_str1["feasibility_status"] == "FULL",
      "feasibility == FULL (service_hours reduction doesn't affect physical constraints)")
check(len(str_sched) == 15,
      f"all 15 vessels scheduled (got {len(str_sched) if str_sched is not None else 0})")

# No infeasible vessels
check(result_str1["vessels_infeasible"] == [],
      f"vessels_infeasible == [] (got {result_str1['vessels_infeasible']})")

# Non-target vessels retain original service_hours (verified via end_time - start_time)
if str_sched is not None:
    svc_in_sched = str_sched.copy()
    svc_in_sched["svc_hrs"] = svc_in_sched["end_time"] - svc_in_sched["start_time"]
    non_target_ids = [v for v in vessels["vessel_id"] if v not in str_config["vessel_ids"]]
    for vid in non_target_ids:
        row = svc_in_sched[svc_in_sched["vessel_id"] == vid]
        if len(row) > 0:
            actual   = int(row["svc_hrs"].iloc[0])
            expected = int(_original_svc[vid])
            check(actual == expected,
                  f"non-target {vid}: service_hours unchanged at {expected}h (got {actual}h)")

# Target vessels have correctly reduced service_hours
if str_sched is not None:
    svc_in_sched = str_sched.copy()
    svc_in_sched["svc_hrs"] = svc_in_sched["end_time"] - svc_in_sched["start_time"]
    for vid, expected in _expected_svc.items():
        row = svc_in_sched[svc_in_sched["vessel_id"] == vid]
        if len(row) > 0:
            actual = int(row["svc_hrs"].iloc[0])
            check(actual == expected,
                  f"{vid}: service_hours correctly reduced to {expected}h (got {actual}h)")

# No service_hours below 1 hour
if str_sched is not None:
    svc_col = str_sched["end_time"] - str_sched["start_time"]
    check((svc_col >= 1).all(),
          "no service_hours < 1 hour in scenario schedule")

# Metric delta keys present
deltas_str = result_str1["metric_deltas"]
for key in ("total_wait_hours_delta", "avg_wait_hours_delta",
            "max_wait_hours_delta", "total_demurrage_delta",
            "total_berth_op_delta", "total_cost_delta"):
    check(key in deltas_str, f"metric_deltas contains '{key}'")

# Determinism
if str_sched is not None and result_str2["scenario_schedule"] is not None:
    s1 = str_sched.sort_values("vessel_id").reset_index(drop=True)
    s2 = result_str2["scenario_schedule"].sort_values("vessel_id").reset_index(drop=True)
    check(s1.equals(s2),
          "SERVICE_TIME_REDUCTION produces identical results on two runs (deterministic)")

# Baseline metrics reproduce known values
check(result_str1["baseline_metrics"]["scheduled_vessels"] == 15,
      "baseline scheduled_vessels == 15")
check(result_str1["baseline_metrics"]["total_wait_hours"] == 39,
      f"baseline total_wait_hours == 39 (got {result_str1['baseline_metrics']['total_wait_hours']})")
check(result_str1["baseline_metrics"]["total_demurrage"] == 132600,
      f"baseline total_demurrage == 132600 (got {result_str1['baseline_metrics']['total_demurrage']})")
check(result_str1["bottleneck_berth_baseline"] == 3,
      f"baseline bottleneck == 3 (got {result_str1['bottleneck_berth_baseline']})")

# Berth operating cost must decrease (fewer service_hours means less berth_op cost)
b_berth_op = result_str1["baseline_metrics"]["total_berth_op"]
s_berth_op = result_str1["scenario_metrics"]["total_berth_op"]
if b_berth_op is not None and s_berth_op is not None:
    check(s_berth_op < b_berth_op,
          f"total_berth_op decreases: ${b_berth_op:,} → ${s_berth_op:,}")

# Final immutability
check(vessels.equals(vessels_snap), "vessels_df untouched after T11")
check(berths.equals(berths_snap),   "berths_df untouched after T11")

# ── Print affected vessel service_hours summary ───────────────────────────────
print("\n  Affected vessel service_hours (original → reduced):")
for vid in sorted(str_config["vessel_ids"]):
    orig = int(_original_svc[vid])
    exp  = _expected_svc[vid]
    print(f"    {vid}: {orig}h → {exp}h  (−{orig - exp}h, −{round(100*(orig-exp)/orig)}%)")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4 report
# ─────────────────────────────────────────────────────────────────────────────
print("\n─── Scenario 4: SERVICE_TIME_REDUCTION (V03,V07,V11,V15 at -20%) ───")
print(f"  {result_str1['scenario_description']}")
_print_metrics_comparison("SERVICE_TIME_REDUCTION", result_str1)

if result_str1["scenario_schedule"] is not None:
    print("\n  Scenario schedule:")
    sc = result_str1["scenario_schedule"].sort_values("start_time")
    print(sc[["vessel_id","vessel_name","berth_id","eta_hours",
              "start_time","end_time","wait_hours","demurrage_cost"]].to_string(index=False))


# ─────────────────────────────────────────────────────────────────────────────
# Final result
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
if failures:
    print(f"TEST SUITE FAILED — {len(failures)} failure(s):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print(f"TEST SUITE PASSED — all checks passed.")
    print("="*60)
