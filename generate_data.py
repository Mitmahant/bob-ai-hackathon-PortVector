import pandas as pd
import os

os.makedirs('data', exist_ok=True)

berths = pd.DataFrame({
    'berth_id': [1, 2, 3, 4, 5],
    'max_ship_length_m': [300, 350, 400, 250, 300],
    'max_draft_m': [14.0, 16.0, 18.0, 12.0, 15.0],
    'cranes_available': [4, 6, 6, 3, 4],
    'hourly_cost_usd': [500, 750, 900, 400, 550]
})
berths.to_csv('data/berths.csv', index=False)

vessels = pd.DataFrame({
    'vessel_id': [f'V{i+1:02d}' for i in range(15)],
    'vessel_name': [f'Container Ship {chr(65+i)}' for i in range(15)],
    'length_m': [240, 310, 380, 220, 280, 330, 390, 200, 260, 340, 370, 210, 290, 320, 360],
    'draft_m': [11.5, 14.5, 16.5, 10.5, 13.0, 15.0, 17.0, 9.5, 12.5, 15.5, 16.8, 10.0, 13.5, 14.8, 16.2],
    'container_count': [1200, 2800, 4500, 900, 2100, 3400, 4800, 800, 1800, 3600, 4200, 950, 2300, 3100, 4100],
    'eta_hours': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    'service_hours': [4, 6, 8, 3, 5, 7, 9, 3, 4, 6, 8, 3, 5, 6, 7],
    'priority': [1, 3, 2, 1, 2, 3, 2, 1, 2, 3, 1, 1, 2, 3, 2],
    'demurrage_cost_per_hour': [1000, 2500, 3500, 800, 1800, 2800, 4000, 750, 1500, 3000, 3800, 850, 2000, 2600, 3400],
    'cargo_value_usd': [5000000, 12000000, 20000000, 3000000, 8000000, 15000000, 22000000, 2500000, 7000000, 16000000, 19000000, 3200000, 9000000, 14000000, 18000000]
})
vessels.to_csv('data/vessels.csv', index=False)
print("SUCCESS: data/berths.csv and data/vessels.csv created!")
