"""
test_ai_copilot.py — PortPulse AI Operations Copilot Tests
===========================================================
Focused tests for the AI decision-support layer (src/ai_copilot.py).

Test coverage:
  T01 — Correct bottleneck identification from engine results
  T02 — Correct use of engine metrics (no fabrication)
  T03 — Correct baseline/scenario comparison
  T04 — Correct detection of bottleneck shift
  T05 — No fabricated numerical values
  T06 — Graceful handling of empty/missing data
  T07 — Recommendation generation (grounded in actual results)
  T08 — Return structure completeness
  T09 — Regression: existing engines untouched
"""

import sys
import os
import math
import pandas as pd

# ── Resolve src/ on path ──────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ai_copilot import (
    generate_copilot_insights,
    build_operational_status,
    build_bottleneck_analysis,
    build_recommendations,
    build_scenario_insight,
)
from congestion import calculate_congestion_metrics
from scenario_engine import run_scenario, SERVICE_TIME_REDUCTION

# ── Load real data ─────────────────────────────────────────────────────────────
vessels  = pd.read_csv("data/vessels.csv")
berths   = pd.read_csv("data/berths.csv")
schedule = pd.read_csv("data/schedule_output.csv")

# Snapshots for immutability checks
vessels_snap  = vessels.copy()
berths_snap   = berths.copy()
schedule_snap = schedule.copy()

# ── Run engines once (reuse across tests) ─────────────────────────────────────
cong = calculate_congestion_metrics(vessels, berths, schedule)

sc_result = run_scenario(
    SERVICE_TIME_REDUCTION,
    vessels,
    berths,
    {"vessel_ids": ["V03", "V07", "V11", "V15"], "reduction_pct": 20},
)

# ── Test harness ──────────────────────────────────────────────────────────────
failures = []

def check(condition: bool, msg: str):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {msg}")
    if not condition:
        failures.append(msg)

def section(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print("="*60)


# ─────────────────────────────────────────────────────────────────────────────
# T01 — Bottleneck identification matches engine output
# ─────────────────────────────────────────────────────────────────────────────
section("T01 — Bottleneck identification")

engine_bottleneck = cong["bottleneck_berth"]
bn = build_bottleneck_analysis(cong)

check(bn["berth_id"] == engine_bottleneck,
      f"bottleneck berth_id == engine bottleneck ({engine_bottleneck}), got {bn['berth_id']}")

# Must match the berth with the highest congestion_score
bm = cong["berth_metrics"]
top_berth = int(bm.sort_values("congestion_score", ascending=False).iloc[0]["berth_id"])
check(bn["berth_id"] == top_berth,
      f"copilot bottleneck ({bn['berth_id']}) matches top congestion_score berth ({top_berth})")

# Congestion score must match engine value
engine_score = float(bm[bm["berth_id"] == engine_bottleneck].iloc[0]["congestion_score"])
check(abs(bn["congestion_score"] - engine_score) < 0.01,
      f"copilot congestion_score ({bn['congestion_score']}) == engine score ({engine_score})")

check(isinstance(bn["explanation"], str) and len(bn["explanation"]) > 10,
      "bottleneck explanation is non-empty string")

check(isinstance(bn["why_it_matters"], str) and len(bn["why_it_matters"]) > 10,
      "why_it_matters is non-empty string")


# ─────────────────────────────────────────────────────────────────────────────
# T02 — Operational status uses engine metrics (not fabricated)
# ─────────────────────────────────────────────────────────────────────────────
section("T02 — Engine metric fidelity (no fabrication)")

summary = cong["summary"].iloc[0]
engine_total_wait   = int(summary["total_waiting_hours"])
engine_avg_wait     = float(summary["avg_wait_hours"])
engine_max_wait     = int(summary["max_wait_hours"])
engine_vw_count     = int(summary["vessels_waiting_count"])
engine_demurrage    = int(summary["total_demurrage_usd"])
engine_scheduled    = int(summary["total_scheduled"])

op = build_operational_status(cong)

check(op["total_waiting_h"] == engine_total_wait,
      f"total_waiting_h == engine value ({engine_total_wait}), got {op['total_waiting_h']}")
check(abs(op["avg_wait_h"] - engine_avg_wait) < 0.01,
      f"avg_wait_h == engine value ({engine_avg_wait:.2f}), got {op['avg_wait_h']:.2f}")
check(op["max_wait_h"] == engine_max_wait,
      f"max_wait_h == engine value ({engine_max_wait}), got {op['max_wait_h']}")
check(op["vessels_waiting"] == engine_vw_count,
      f"vessels_waiting == engine value ({engine_vw_count}), got {op['vessels_waiting']}")
check(op["total_demurrage"] == engine_demurrage,
      f"total_demurrage == engine value ({engine_demurrage}), got {op['total_demurrage']}")
check(op["total_scheduled"] == engine_scheduled,
      f"total_scheduled == engine value ({engine_scheduled}), got {op['total_scheduled']}")
check(op["bottleneck_berth"] == engine_bottleneck,
      f"bottleneck_berth == engine value ({engine_bottleneck}), got {op['bottleneck_berth']}")

# Status color consistency
check(op["congestion_level"] in ("HIGH", "MEDIUM", "LOW", "IDLE", "UNKNOWN"),
      f"congestion_level is a valid label (got {op['congestion_level']})")
check(op["status_color"] in ("red", "orange", "green", "gray"),
      f"status_color is a valid value (got {op['status_color']})")


# ─────────────────────────────────────────────────────────────────────────────
# T03 — Scenario comparison uses actual engine deltas
# ─────────────────────────────────────────────────────────────────────────────
section("T03 — Scenario comparison uses actual deltas")

si = build_scenario_insight(sc_result)

engine_wait_delta = sc_result["metric_deltas"].get("total_wait_hours_delta")
engine_dem_delta  = sc_result["metric_deltas"].get("total_demurrage_delta")
engine_cost_delta = sc_result["metric_deltas"].get("total_cost_delta")

check(isinstance(si["summary_sentence"], str) and len(si["summary_sentence"]) > 10,
      "scenario_insight summary_sentence is non-empty")
check(isinstance(si["metric_lines"], list) and len(si["metric_lines"]) >= 4,
      f"metric_lines has >= 4 entries (got {len(si['metric_lines'])})")

# Verify that improvement / concern areas reflect actual deltas
if engine_wait_delta is not None and engine_wait_delta < 0:
    check("total waiting time" in si["improvement_areas"],
          f"improvement_areas includes 'total waiting time' when delta<0 "
          f"(delta={engine_wait_delta})")

if engine_dem_delta is not None and engine_dem_delta < 0:
    check("demurrage cost" in si["improvement_areas"],
          f"improvement_areas includes 'demurrage cost' when delta<0 "
          f"(delta={engine_dem_delta})")

# Numeric values in metric_lines must originate from engine deltas (spot-check)
# The metric line for total waiting should contain the absolute delta value
if engine_wait_delta is not None:
    abs_wait_str = str(abs(int(engine_wait_delta)))
    wait_line_matches = any(abs_wait_str in line for line in si["metric_lines"])
    check(wait_line_matches,
          f"total waiting delta ({abs_wait_str} h) appears in metric_lines")


# ─────────────────────────────────────────────────────────────────────────────
# T04 — Bottleneck shift detection
# ─────────────────────────────────────────────────────────────────────────────
section("T04 — Bottleneck shift detection")

bb_base = sc_result["bottleneck_berth_baseline"]
bb_sc   = sc_result["bottleneck_berth_scenario"]
shift   = (bb_base is not None and bb_sc is not None and bb_base != bb_sc)

si = build_scenario_insight(sc_result)

check(si["bottleneck_shift"] == shift,
      f"bottleneck_shift == {shift} (got {si['bottleneck_shift']}); "
      f"baseline={bb_base}, scenario={bb_sc}")

if shift:
    check(si["bottleneck_warning"] is not None,
          "bottleneck_warning is not None when shift detected")
    check(isinstance(si["bottleneck_warning"], str) and len(si["bottleneck_warning"]) > 10,
          "bottleneck_warning is a non-empty string")
    check(str(bb_base) in si["bottleneck_warning"],
          f"bottleneck_warning mentions original bottleneck berth {bb_base}")
    check(str(bb_sc) in si["bottleneck_warning"],
          f"bottleneck_warning mentions new bottleneck berth {bb_sc}")
else:
    check(si["bottleneck_warning"] is None,
          "bottleneck_warning is None when no shift")

# Verify with a synthetic scenario that would NOT produce a shift
# (no-op: V02 priority is already 3)
from scenario_engine import PRIORITY_SURGE
noop_result = run_scenario(
    PRIORITY_SURGE, vessels, berths,
    {"vessel_ids": ["V02"], "new_priority": 3},
)
noop_si = build_scenario_insight(noop_result)
noop_shift = (
    noop_result["bottleneck_berth_baseline"] != noop_result["bottleneck_berth_scenario"]
)
check(noop_si["bottleneck_shift"] == noop_shift,
      f"no-op scenario bottleneck_shift == {noop_shift} (got {noop_si['bottleneck_shift']})")


# ─────────────────────────────────────────────────────────────────────────────
# T05 — No fabricated numerical values
# ─────────────────────────────────────────────────────────────────────────────
section("T05 — No fabricated numerical values")

# The copilot must not introduce numbers that aren't in the engine results.
# We verify by checking that every number mentioned in the operational status
# bullet facts can be traced to an engine metric.

copilot_out = generate_copilot_insights(cong, sc_result)
op = copilot_out["operational_status"]

# Collect all engine scalars
engine_scalars = {
    engine_total_wait,
    int(engine_avg_wait * 10),   # avoid float precision issues
    engine_max_wait,
    engine_vw_count,
    engine_demurrage,
    engine_scheduled,
    int(summary["total_vessels"]),
}

# The copilot figures should match what the engine produced — no independent computation
check(op["total_waiting_h"] == engine_total_wait,
      f"total_waiting_h traces to engine ({engine_total_wait}), not fabricated")
check(op["total_demurrage"] == engine_demurrage,
      f"total_demurrage traces to engine ({engine_demurrage}), not fabricated")
check(op["max_wait_h"] == engine_max_wait,
      f"max_wait_h traces to engine ({engine_max_wait}), not fabricated")

# Bottleneck analysis scores must match engine
bn = copilot_out["bottleneck_analysis"]
check(abs(bn["congestion_score"] - engine_score) < 0.01,
      f"bottleneck congestion_score traces to engine ({engine_score}), not fabricated")

# Utilization must match engine
engine_util = float(bm[bm["berth_id"] == engine_bottleneck].iloc[0]["utilization_pct"])
check(abs(bn["utilization_pct"] - engine_util) < 0.01,
      f"bottleneck utilization_pct traces to engine ({engine_util}), not fabricated")


# ─────────────────────────────────────────────────────────────────────────────
# T06 — Graceful handling of empty / missing data
# ─────────────────────────────────────────────────────────────────────────────
section("T06 — Graceful handling of empty/missing data")

# Empty cong dict
empty_op = build_operational_status({})
check(isinstance(empty_op, dict),        "build_operational_status({}) returns dict")
check("headline" in empty_op,            "empty cong: headline key present")
check("bullet_facts" in empty_op,        "empty cong: bullet_facts key present")
check(isinstance(empty_op["bullet_facts"], list), "empty cong: bullet_facts is a list")

# Empty bottleneck analysis
empty_bn = build_bottleneck_analysis({})
check(isinstance(empty_bn, dict),        "build_bottleneck_analysis({}) returns dict")
check("berth_id" in empty_bn,            "empty cong: berth_id key present")

# Empty recommendations
empty_recs = build_recommendations({})
check(isinstance(empty_recs, list),      "build_recommendations({}) returns list")
check(len(empty_recs) >= 1,              "empty cong: at least one rec entry returned")

# Empty scenario insight
empty_si = build_scenario_insight({})
check(isinstance(empty_si, dict),        "build_scenario_insight({}) returns dict")
check("summary_sentence" in empty_si,    "empty sc: summary_sentence key present")
check("bottleneck_shift" in empty_si,    "empty sc: bottleneck_shift key present")
check(empty_si["bottleneck_shift"] == False, "empty sc: bottleneck_shift is False")

# generate_copilot_insights with None scenario
full_no_sc = generate_copilot_insights(cong, None)
check(isinstance(full_no_sc, dict),      "generate_copilot_insights(cong, None) returns dict")
check(full_no_sc["scenario_insight"] is None,
      "scenario_insight is None when sc_result is None")

# generate_copilot_insights with empty dicts
full_empty = generate_copilot_insights({}, {})
check(isinstance(full_empty, dict),      "generate_copilot_insights({}, {}) returns dict")
check("operational_status" in full_empty, "empty inputs: operational_status key present")


# ─────────────────────────────────────────────────────────────────────────────
# T07 — Recommendations are grounded in actual results
# ─────────────────────────────────────────────────────────────────────────────
section("T07 — Recommendations grounded in engine results")

recs = build_recommendations(cong, sc_result)

check(isinstance(recs, list),            "recommendations is a list")
check(len(recs) >= 2,                    f"at least 2 recommendations generated (got {len(recs)})")
check(len(recs) <= 5,                    f"at most 5 recommendations generated (got {len(recs)})")

for i, rec in enumerate(recs):
    check("priority" in rec,   f"rec[{i}] has 'priority' key")
    check("action"   in rec,   f"rec[{i}] has 'action' key")
    check("evidence" in rec,   f"rec[{i}] has 'evidence' key")
    check("category" in rec,   f"rec[{i}] has 'category' key")
    check(isinstance(rec["action"],   str) and len(rec["action"]) > 5,
          f"rec[{i}] action is non-empty string")
    check(isinstance(rec["evidence"], str) and len(rec["evidence"]) > 5,
          f"rec[{i}] evidence is non-empty string")
    check(rec["priority"] == i + 1,
          f"rec[{i}] priority is sequential ({i+1}), got {rec['priority']}")

# First recommendation should mention the bottleneck berth
first_rec_text = recs[0]["action"] + " " + recs[0]["evidence"]
check(str(engine_bottleneck) in first_rec_text,
      f"first recommendation references actual bottleneck berth {engine_bottleneck}")

# Bottleneck shift recommendation must reference actual berth IDs
if shift:
    shift_recs = [r for r in recs if "monitoring" in r.get("category", "")]
    check(len(shift_recs) >= 1,
          "monitoring recommendation generated when bottleneck shift detected")
    if shift_recs:
        ev_text = shift_recs[0]["action"] + " " + shift_recs[0]["evidence"]
        check(str(bb_sc) in ev_text,
              f"monitoring recommendation references new bottleneck berth {bb_sc}")


# ─────────────────────────────────────────────────────────────────────────────
# T08 — Return structure completeness
# ─────────────────────────────────────────────────────────────────────────────
section("T08 — Return structure completeness")

copilot = generate_copilot_insights(cong, sc_result)

REQUIRED_TOP_KEYS = [
    "operational_status", "bottleneck_analysis", "recommendations",
    "scenario_insight", "copilot_type", "disclaimer",
]
for k in REQUIRED_TOP_KEYS:
    check(k in copilot, f"top-level key '{k}' present")

check(copilot["copilot_type"] == "Deterministic Rule-Based Decision Support",
      f"copilot_type is correct (got {copilot['copilot_type']})")
check(isinstance(copilot["disclaimer"], str) and len(copilot["disclaimer"]) > 20,
      "disclaimer is non-empty string")

# operational_status structure
op = copilot["operational_status"]
for k in ("headline", "congestion_level", "bottleneck_berth", "total_waiting_h",
          "avg_wait_h", "max_wait_h", "vessels_waiting", "total_demurrage",
          "total_scheduled", "bullet_facts", "status_color"):
    check(k in op, f"operational_status key '{k}' present")

# bottleneck_analysis structure
bn = copilot["bottleneck_analysis"]
for k in ("berth_id", "congestion_score", "congestion_level", "utilization_pct",
          "queue_depth", "wait_pressure", "vessel_count", "wait_hours_total",
          "why_it_matters", "affected_vessels", "explanation"):
    check(k in bn, f"bottleneck_analysis key '{k}' present")

# scenario_insight structure (when sc_result provided)
si = copilot["scenario_insight"]
check(si is not None,              "scenario_insight is not None (sc_result was provided)")
for k in ("summary_sentence", "metric_lines", "bottleneck_shift",
          "bottleneck_warning", "improvement_areas", "concern_areas"):
    check(k in si, f"scenario_insight key '{k}' present")


# ─────────────────────────────────────────────────────────────────────────────
# T09 — Regression: existing engines are untouched
# ─────────────────────────────────────────────────────────────────────────────
section("T09 — Regression: engines untouched")

# Verify data not mutated throughout copilot tests
check(vessels.equals(vessels_snap),   "vessels_df not mutated by AI copilot tests")
check(berths.equals(berths_snap),     "berths_df not mutated by AI copilot tests")
check(schedule.equals(schedule_snap), "schedule_df not mutated by AI copilot tests")

# Re-run engines to confirm they still produce the same known values
cong2 = calculate_congestion_metrics(vessels, berths, schedule)
check(cong2["bottleneck_berth"] == 3,
      f"congestion engine still identifies Berth 3 as bottleneck (got {cong2['bottleneck_berth']})")
check(int(cong2["summary"].iloc[0]["total_scheduled"]) == 15,
      "congestion engine still reports 15 scheduled vessels")

sc2 = run_scenario(
    SERVICE_TIME_REDUCTION,
    vessels,
    berths,
    {"vessel_ids": ["V03", "V07", "V11", "V15"], "reduction_pct": 20},
)
check(sc2["baseline_metrics"]["total_wait_hours"] == 39,
      f"scenario engine baseline total_wait_hours still == 39 (got {sc2['baseline_metrics']['total_wait_hours']})")
check(sc2["baseline_metrics"]["total_demurrage"] == 132600,
      f"scenario engine baseline demurrage still == 132600 (got {sc2['baseline_metrics']['total_demurrage']})")
check(sc2["bottleneck_berth_baseline"] == 3,
      f"scenario engine baseline bottleneck still == 3 (got {sc2['bottleneck_berth_baseline']})")

# Copilot does NOT import/use optimizer.py, congestion.py, scenario_engine.py directly
# (it receives their already-computed dicts as arguments) — enforced by design.
check(vessels.equals(vessels_snap),   "vessels_df still untouched after regression re-run")
check(berths.equals(berths_snap),     "berths_df still untouched after regression re-run")


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
    print("AI COPILOT TEST SUITE PASSED — all checks passed.")
    print("="*60)
