import sys
import pandas as pd
from optimizer import optimize_port_schedule

# ── 1. Load data ─────────────────────────────────────────────────────────────
vessels = pd.read_csv("data/vessels.csv")
berths  = pd.read_csv("data/berths.csv")

print(f"Loaded {len(vessels)} vessels and {len(berths)} berths.")

# ── 2. Solve ──────────────────────────────────────────────────────────────────
schedule = optimize_port_schedule(vessels, berths)

if schedule is None:
    print("\n[INFEASIBLE] The optimizer returned no solution.")
    sys.exit(1)

# ── 3. Save ───────────────────────────────────────────────────────────────────
out_cols = ["vessel_id", "vessel_name", "berth_id",
            "eta_hours", "start_time", "end_time",
            "wait_hours", "demurrage_cost", "berth_operating_cost", "total_cost"]
schedule[out_cols].to_csv("data/schedule_output.csv", index=False)
print("\n[SAVED] data/schedule_output.csv")

# ── 4. Print complete schedule ────────────────────────────────────────────────
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 0)
print("\n=== COMPLETE SCHEDULE ===")
print(schedule[out_cols].sort_values("start_time").to_string(index=False))

# ── 4b. Cost summary ──────────────────────────────────────────────────────────
total_demurrage = schedule["demurrage_cost"].sum()
total_berth_op  = schedule["berth_operating_cost"].sum()
total_all       = schedule["total_cost"].sum()
print(f"\n=== COST SUMMARY ===")
print(f"  Total demurrage cost      : ${total_demurrage:>12,.0f}")
print(f"  Total berth operating cost: ${total_berth_op:>12,.0f}")
print(f"  Total combined cost       : ${total_all:>12,.0f}")

# ── 5. Validate ───────────────────────────────────────────────────────────────
MAX_HORIZON = 72
errors = []

# Build lookup maps
vessel_map = vessels.set_index("vessel_id").to_dict("index")
berth_map  = berths.set_index("berth_id").to_dict("index")

assigned_vessel_ids = set(schedule["vessel_id"].tolist())
total_vessels = len(vessels)

print(f"\n=== VALIDATION ===")
print(f"Vessels scheduled : {len(schedule)} / {total_vessels}")

# Check for unassigned vessels
unassigned = [v for v in vessels["vessel_id"] if v not in assigned_vessel_ids]
if unassigned:
    errors.append(f"[UNASSIGNED] {len(unassigned)} vessel(s) not in schedule: {unassigned}")

for _, row in schedule.iterrows():
    vid  = row["vessel_id"]
    bid  = row["berth_id"]
    eta  = row["eta_hours"]
    st   = row["start_time"]
    et   = row["end_time"]

    # Length constraint
    v_len = vessel_map[vid]["length_m"]
    b_len = berth_map[bid]["max_ship_length_m"]
    if v_len > b_len:
        errors.append(
            f"[LENGTH] {vid} length {v_len}m > berth {bid} max {b_len}m"
        )

    # Draft constraint
    v_draft = vessel_map[vid]["draft_m"]
    b_draft = berth_map[bid]["max_draft_m"]
    if v_draft > b_draft:
        errors.append(
            f"[DRAFT] {vid} draft {v_draft}m > berth {bid} max {b_draft}m"
        )

    # No start before ETA
    if st < eta:
        errors.append(
            f"[ETA] {vid} starts at h{st} but ETA is h{eta}"
        )

    # Within planning horizon
    if et > MAX_HORIZON:
        errors.append(
            f"[HORIZON] {vid} ends at h{et} which exceeds 72-hour horizon"
        )

# No overlapping service intervals per berth
for bid, grp in schedule.groupby("berth_id"):
    intervals = sorted(grp[["vessel_id", "start_time", "end_time"]].values.tolist(),
                       key=lambda r: r[1])
    for i in range(len(intervals) - 1):
        v_a, s_a, e_a = intervals[i]
        v_b, s_b, e_b = intervals[i + 1]
        if s_b < e_a:
            errors.append(
                f"[OVERLAP] Berth {bid}: {v_a} (h{s_a}–h{e_a}) overlaps "
                f"{v_b} (h{s_b}–h{e_b})"
            )

if errors:
    print("\n[VALIDATION FAILED]")
    for e in errors:
        print(" ", e)
    sys.exit(2)
else:
    print("\n[VALIDATION PASSED] All constraints satisfied.")
    print(f"  ✓ Length constraints     : OK")
    print(f"  ✓ Draft constraints      : OK")
    print(f"  ✓ No start before ETA   : OK")
    print(f"  ✓ No berth overlaps      : OK")
    print(f"  ✓ Within 72-hour horizon : OK")
    if unassigned:
        print(f"\n[NOTE] {len(unassigned)} vessel(s) infeasible (no qualifying berth or horizon): {unassigned}")
        sys.exit(3)

print(f"\n15-vessel schedule: {'FULLY FEASIBLE' if not unassigned else 'PARTIALLY FEASIBLE — see NOTE above'}")
