# Setup Guide — PortPulse AI

> This project requires **no API keys, no cloud accounts, and no external services**.
> It runs entirely locally with Python + pip.

---

## Prerequisites

- Python 3.10 or later
- pip (comes with Python)
- A terminal / command line

No environment variables are required to run the dashboard or tests.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Mitmahant/bob-ai-hackathon-PortVector.git
cd bob-ai-hackathon-PortVector

# 2. Install dependencies (takes ~1–2 minutes)
pip install -r requirements.txt

# Or use the setup script:
bash setup.sh
```

**Dependencies installed:**
- `streamlit` — dashboard framework
- `pandas` — data manipulation
- `numpy` — numerical utilities
- `ortools` — OR-Tools SCIP MIP optimizer (Google)
- `plotly` — interactive charts

---

## Running the Dashboard

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

The dashboard loads immediately — the pre-computed optimizer schedule
(`data/schedule_output.csv`) and all required data files are already committed.

---

## Running Tests

```bash
# Core engine tests
python test_optimizer.py
python test_congestion.py
python test_scenario_engine.py

# AI Copilot tests (100 assertion checks)
python test_ai_copilot.py

# Optimizer + schedule validation (end-to-end)
python run_optimizer.py
```

All test suites print `TEST SUITE PASSED` on success and exit with code 1 on failure.

---

## Regenerating Data (Optional)

The `data/` directory is pre-populated. To regenerate from scratch:

```bash
python generate_data.py     # regenerates data/vessels.csv and data/berths.csv
python run_optimizer.py     # re-runs optimizer, regenerates data/schedule_output.csv
streamlit run app.py        # launch dashboard with fresh data
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'ortools'` | Run `pip install -r requirements.txt` again |
| `ModuleNotFoundError: No module named 'streamlit'` | Run `pip install streamlit` |
| `FileNotFoundError: data/vessels.csv` | Run `python generate_data.py && python run_optimizer.py` |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` |
| Slow first load | The optimizer runs once per session — subsequent interactions are fast |

---

## Notes

- No `.env` file is needed. The `src/.env.example` is a template retained from the
  project scaffold — it is not used by PortPulse AI.
- No database, no authentication, no cloud services.
- The AI Operations Copilot is entirely local and deterministic — it requires
  no API keys.
