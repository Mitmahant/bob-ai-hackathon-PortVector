import pandas as pd
from ortools.linear_solver import pywraplp

def optimize_port_schedule(vessels_df, berths_df, max_horizon_hours=72):
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return None

    vessels = vessels_df.to_dict('records')
    berths = berths_df.to_dict('records')

    x = {}
    for v_idx, v in enumerate(vessels):
        for b_idx, b in enumerate(berths):
            if v['length_m'] <= b['max_ship_length_m'] and v['draft_m'] <= b['max_draft_m']:
                for t in range(int(v['eta_hours']), max_horizon_hours - int(v['service_hours']) + 1):
                    x[v_idx, b_idx, t] = solver.BoolVar(f'x_{v_idx}_{b_idx}_{t}')

    for v_idx in range(len(vessels)):
        solver.Add(sum(x[v_idx, b_idx, t] for b_idx, b in enumerate(berths) for t in range(max_horizon_hours) if (v_idx, b_idx, t) in x) == 1)

    for b_idx in range(len(berths)):
        for t in range(max_horizon_hours):
            overlapping = []
            for v_idx, v in enumerate(vessels):
                s_hrs = int(v['service_hours'])
                for t_prime in range(max(0, t - s_hrs + 1), t + 1):
                    if (v_idx, b_idx, t_prime) in x:
                        overlapping.append(x[v_idx, b_idx, t_prime])
            if overlapping:
                solver.Add(sum(overlapping) <= 1)

    # Build a berth index map for O(1) lookup inside the loop
    berth_by_idx = {b_idx: b for b_idx, b in enumerate(berths)}

    objective = solver.Objective()
    for (v_idx, b_idx, t), var in x.items():
        v = vessels[v_idx]
        b = berth_by_idx[b_idx]
        # Demurrage: wait * rate * priority  (higher priority → larger penalty for delay)
        wait_time = t - v['eta_hours']
        demurrage = wait_time * v['demurrage_cost_per_hour'] * v['priority']
        # Berth operating cost: fixed cost for occupying this berth for the service window
        berth_op = v['service_hours'] * b['hourly_cost_usd']
        cost = demurrage + berth_op
        objective.SetCoefficient(var, float(cost))

    objective.SetMinimization()
    status = solver.Solve()

    if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        results = []
        for (v_idx, b_idx, t), var in x.items():
            if var.solution_value() > 0.5:
                v = vessels[v_idx]
                b = berths[b_idx]
                start_t = t
                end_t = t + int(v['service_hours'])
                wait_t = start_t - int(v['eta_hours'])
                demurrage = wait_t * v['demurrage_cost_per_hour']
                berth_op  = int(v['service_hours']) * b['hourly_cost_usd']
                results.append({
                    'vessel_id': v['vessel_id'],
                    'vessel_name': v['vessel_name'],
                    'berth_id': b['berth_id'],
                    'eta_hours': v['eta_hours'],
                    'start_time': start_t,
                    'end_time': end_t,
                    'wait_hours': wait_t,
                    'demurrage_cost': demurrage,
                    'berth_operating_cost': berth_op,
                    'total_cost': demurrage + berth_op
                })
        return pd.DataFrame(results)
    return None
