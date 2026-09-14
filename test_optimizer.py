import pandas as pd
from optimizer import optimize_port_schedule

vessels = pd.DataFrame([
    {'vessel_id': 'V01', 'vessel_name': 'Ship 1', 'length_m': 200, 'draft_m': 10.0, 'eta_hours': 2, 'service_hours': 4, 'priority': 2, 'demurrage_cost_per_hour': 1000},
    {'vessel_id': 'V02', 'vessel_name': 'Ship 2', 'length_m': 250, 'draft_m': 12.0, 'eta_hours': 3, 'service_hours': 5, 'priority': 3, 'demurrage_cost_per_hour': 2000},
    {'vessel_id': 'V03', 'vessel_name': 'Ship 3', 'length_m': 220, 'draft_m': 11.0, 'eta_hours': 6, 'service_hours': 3, 'priority': 1, 'demurrage_cost_per_hour': 800}
])

berths = pd.DataFrame([
    {'berth_id': 1, 'max_ship_length_m': 300, 'max_draft_m': 15.0, 'hourly_cost_usd': 0},
    {'berth_id': 2, 'max_ship_length_m': 300, 'max_draft_m': 15.0, 'hourly_cost_usd': 0}
])

result = optimize_port_schedule(vessels, berths)
print("\n--- OPTIMIZER TEST RESULT ---")
print(result[['vessel_id', 'berth_id', 'eta_hours', 'start_time', 'end_time', 'wait_hours']])
