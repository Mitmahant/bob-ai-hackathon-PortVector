"""
test_congestion.py — PortPulse AI: Congestion Engine Tests
===========================================================
Verifies calculate_congestion_metrics() against the real
optimizer-generated schedule.  All assertions are explicit
and fail loudly with a descriptive message.
"""

import sys
import pandas as pd
from congestion import calculate_congestion_metrics

# ── Load real data ────────────────────────────────────────────────────────────
vessels  = pd.read_csv("data/vessels.csv")
berths   = pd.read_csv("data/berths.csv")
schedule = pd.read_csv("data/schedule_output.csv")

# Snapshot originals to verify the function doesn't mutate them
vessels_snapshot  = vessels.copy()
berths_snapshot   = berths.copy()
schedule_snapshot = schedule.copy()

print("=" * 60)
print("PortPulse AI — Congestion Engine Test Suite")
print("=" * 60)
print(f"Input:  {len(vessels)} vessels, {len(berths)} berths, "
      f"{len(schedule)} scheduled assignments\n")

# ── Run ───────────────────────────────────────────────────────────────────────
result = calculate_congestion_metrics(vessels, berths, schedule)

failures = []

def check(condition: bool, msg: str):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {msg}")
    if not condition:
        failures.append(msg)


# ── T01 — Return structure ────────────────────────────────────────────────────
print("T01 — Return structure")
for key in ("summary", "berth_metrics", "vessel_flags", "hotspot_periods",
            "bottleneck_berth", "metadata"):
    check(key in result, f"result contains key '{key}'")

# ── T02 — Summary metrics produced and sane ──────────────────────────────────
print("\nT02 — Fleet-wide summary")
summary = result["summary"]
check(isinstance(summary, pd.DataFrame),          "summary is a DataFrame")
check(len(summary) == 1,                           "summary has exactly one row")
check(summary["total_vessels"].iloc[0] == 15,      "total_vessels == 15")
check(summary["total_scheduled"].iloc[0] == 15,    "total_scheduled == 15")
check(summary["total_service_hours"].iloc[0] > 0,  "total_service_hours > 0")
check(summary["total_waiting_hours"].iloc[0] >= 0, "total_waiting_hours >= 0")
check(summary["avg_wait_hours"].iloc[0] >= 0,      "avg_wait_hours >= 0")
check(summary["max_wait_hours"].iloc[0] >= 0,      "max_wait_hours >= 0")
check(summary["vessels_waiting_count"].iloc[0] >= 0, "vessels_waiting_count >= 0")

# ── T03 — All 5 berths present in berth_metrics ──────────────────────────────
print("\nT03 — Berth coverage")
bm = result["berth_metrics"]
check(isinstance(bm, pd.DataFrame),    "berth_metrics is a DataFrame")
check(len(bm) == 5,                    "berth_metrics has 5 rows (all berths)")
check(set(bm["berth_id"].tolist()) == {1, 2, 3, 4, 5},
      "berth_metrics contains berth_ids 1–5")

# ── T04 — Utilization values are valid ───────────────────────────────────────
print("\nT04 — Utilization validity")
check((bm["utilization_pct"] >= 0).all(),   "all utilization_pct >= 0")
check((bm["utilization_pct"] <= 100).all(), "all utilization_pct <= 100")

# ── T05 — Congestion scores are valid ────────────────────────────────────────
print("\nT05 — Congestion scores")
check((bm["congestion_score"] >= 0).all(),   "all congestion_score >= 0")
check((bm["congestion_score"] <= 100).all(), "all congestion_score <= 100")
check(bm["congestion_level"].isin(
    ["HIGH", "MEDIUM", "LOW", "IDLE"]).all(),
    "all congestion_level values are valid labels")

# ── T06 — Waiting metrics are non-negative ───────────────────────────────────
print("\nT06 — Waiting metrics non-negative")
check((bm["wait_hours_total"] >= 0).all(),  "berth wait_hours_total >= 0")
check((bm["wait_hours_mean"]  >= 0).all(),  "berth wait_hours_mean  >= 0")
check((bm["wait_hours_max"]   >= 0).all(),  "berth wait_hours_max   >= 0")
vf = result["vessel_flags"]
check(isinstance(vf, pd.DataFrame),         "vessel_flags is a DataFrame")
if len(vf) > 0:
    check((vf["wait_hours"] > 0).all(),     "all flagged vessels have wait_hours > 0")
    check(vf["wait_severity"].isin(
        ["CRITICAL", "HIGH", "MODERATE", "LOW"]).all(),
        "all wait_severity values are valid labels")

# ── T07 — Bottleneck berth identifiable ──────────────────────────────────────
print("\nT07 — Bottleneck identification")
bb = result["bottleneck_berth"]
check(isinstance(bb, int),         "bottleneck_berth is an int")
check(bb in {1, 2, 3, 4, 5},       f"bottleneck_berth ({bb}) is a valid berth_id")
# The berth with the highest congestion score should be the bottleneck
top_score_berth = int(bm.sort_values("congestion_score", ascending=False).iloc[0]["berth_id"])
check(bb == top_score_berth,
      f"bottleneck_berth ({bb}) matches highest congestion_score berth ({top_score_berth})")

# ── T08 — Hotspot periods ─────────────────────────────────────────────────────
print("\nT08 — Hotspot periods")
hp = result["hotspot_periods"]
check(isinstance(hp, pd.DataFrame),  "hotspot_periods is a DataFrame")
check(len(hp) == 72,                  "hotspot_periods has 72 rows (one per hour)")
check((hp["hour"] == list(range(72))).all(), "hours 0–71 are present in order")
check((hp["berths_occupied"] >= 0).all(),    "berths_occupied >= 0 every hour")
check((hp["port_load_pct"] >= 0).all(),      "port_load_pct >= 0 every hour")
check((hp["port_load_pct"] <= 100).all(),    "port_load_pct <= 100 every hour")
check("is_hotspot" in hp.columns,            "is_hotspot column present")

# ── T09 — Input data not mutated ─────────────────────────────────────────────
print("\nT09 — Immutability (optimizer/schedule not modified)")
check(vessels.equals(vessels_snapshot),    "vessels_df not mutated")
check(berths.equals(berths_snapshot),      "berths_df not mutated")
check(schedule.equals(schedule_snapshot),  "schedule_df not mutated")

# ── T10 — Metadata present and descriptive ────────────────────────────────────
print("\nT10 — Metadata / audit trail")
meta = result["metadata"]
check(isinstance(meta, dict),                     "metadata is a dict")
check("method" in meta,                           "metadata contains 'method'")
check("congestion_score_formula" in meta,         "metadata contains score formula")
check("disclaimer" in meta,                       "metadata contains disclaimer")
check("NOT" in meta["disclaimer"].upper() or
      "NOT" in meta["method"].upper(),
      "metadata explicitly states this is NOT a trained model")

# ── Results summary ───────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("CONGESTION METRICS REPORT")
print("=" * 60)

print("\n--- Fleet-wide Summary ---")
print(summary.to_string(index=False))

print("\n--- Per-Berth Congestion Metrics (ranked by congestion score) ---")
display_cols = [
    "berth_id", "vessel_count", "service_hours_total", "utilization_pct",
    "wait_hours_total", "wait_hours_mean", "queue_depth_ratio",
    "wait_pressure", "congestion_score", "congestion_level"
]
print(bm[display_cols].to_string(index=False))

print(f"\n--- Bottleneck Berth: {bb} ---")
bottleneck_row = bm[bm["berth_id"] == bb].iloc[0]
print(f"  Congestion score   : {bottleneck_row['congestion_score']}")
print(f"  Congestion level   : {bottleneck_row['congestion_level']}")
print(f"  Vessel count       : {bottleneck_row['vessel_count']}")
print(f"  Utilization        : {bottleneck_row['utilization_pct']}%")
print(f"  Total wait hours   : {bottleneck_row['wait_hours_total']}")

print("\n--- Vessels Flagged for Significant Waiting ---")
if len(vf) > 0:
    print(vf[["vessel_id", "vessel_name", "berth_id", "wait_hours",
               "demurrage_cost", "priority", "wait_severity"]].to_string(index=False))
else:
    print("  None — all vessels started at or before ETA.")

print("\n--- Hourly Port Load (first 40 hours shown, hotspots marked) ---")
hp_display = hp[hp["hour"] < 40].copy()
hp_display["hotspot"] = hp_display["is_hotspot"].map({True: "*** HOTSPOT ***", False: ""})
print(hp_display[["hour", "berths_occupied", "vessels_in_service",
                   "vessels_at_anchor", "port_load_pct", "hotspot"]].to_string(index=False))

peak_hour = hp.loc[hp["port_load_pct"].idxmax()]
print(f"\n  Peak port load: {peak_hour['port_load_pct']}% "
      f"at hour {int(peak_hour['hour'])} "
      f"({int(peak_hour['vessels_in_service'])} vessels in service)")

hotspot_count = hp["is_hotspot"].sum()
print(f"  Hotspot hours (>= 60% port load): {hotspot_count}")

# ── Final result ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failures:
    print(f"TEST SUITE FAILED — {len(failures)} failure(s):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print(f"TEST SUITE PASSED — all checks passed.")
    print("=" * 60)
