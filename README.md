
# 🚢 PortPulse AI — Container Congestion Predictor & Port Operations Optimiser

> **Problem Statement L1 — Hackathon Demonstration**
> ⚠️ All data is **simulated** for demo purposes. No live port data is used.

---

## 👥 Team

| Field                        | Details                                                 |
| ---------------------------- | ------------------------------------------------------- |
| **Team Name**          | Portvector                                              |
| **Track**              | AI — IBM BoB AI Innovation Hackathon 2026              |
| **Team Leader**        | Mit Mahant — 26DIT022 — 26dit022@charusat.edu.in      |
| **Member 2**           | Brijraj Solanki — 26DIT056 — 26dit056@charusat.edu.in |
| **Member 3**           | Pival Patel — 26DIT045 — 26dit045@charusat.edu.in     |
| **Member 4**           | Arpan Ghaskata — 26DIT011 — 26dit011@charusat.edu.in  |
| **Branch / Institute** | IT — DEPSTAR                                           |

---

## 🎯 Problem Statement

Container port operations suffer from reactive congestion management: operators only
discover berth bottlenecks after vessels have already accumulated hours of waiting,
generating significant demurrage costs and supply-chain delays.

Port planners need a forward-looking tool that can identify bottlenecks before they
cascade, model operational interventions, and generate clear decision-support
recommendations — all within a single operational view.

---

## 💡 Solution

**PortPulse AI** is a Streamlit-based operational dashboard that combines a
MIP-based berth scheduling optimizer, a deterministic congestion analysis engine,
a what-if scenario engine, and a rule-based AI Operations Copilot to give port
operators a complete 72-hour operational picture plus actionable decision support.

The system takes simulated vessel and berth data, runs an OR-Tools MIP optimizer to
produce the optimal 72-hour schedule, scores every berth using a transparent
analytical congestion index, evaluates operational scenarios (e.g. service-time
reductions), and delivers AI-generated insights and recommendations that are
grounded exclusively in the calculated engine outputs — no values are fabricated.

---

## ✨ Key Features

- **MIP Berth Scheduler:** OR-Tools SCIP optimizer allocates 15 vessels across 5 berths, minimizing priority-weighted demurrage and berth operating cost.
- **Congestion Analysis Engine:** Transparent analytical congestion scoring per berth — utilization, queue depth, wait pressure, and throughput load — ranked and visualized.
- **What-If Scenario Engine:** Models operational interventions (service-time reduction, arrival surge, priority changes, berth unavailability) by re-running the optimizer on modified inputs.
- **AI Operations Copilot:** Deterministic rule-based decision-support layer that interprets engine results and generates: operational status, bottleneck analysis, priority actions with evidence, scenario insights, and bottleneck-shift warnings.
- **Interactive 72-Hour Gantt:** Full optimizer-generated schedule with waiting time visualization and berth-by-berth service breakdown.

---

## 🛠️ Tech Stack

| Category                | Technologies                                        |
| ----------------------- | --------------------------------------------------- |
| **Language**      | Python 3.10+                                        |
| **Optimizer**     | OR-Tools (Google) — SCIP MIP solver                |
| **Dashboard**     | Streamlit                                           |
| **Data**          | pandas, numpy                                       |
| **Visualization** | Plotly                                              |
| **AI Copilot**    | Deterministic rule-based (no external API required) |

---

## 📁 Repository Structure

```
├── app.py                  # Streamlit dashboard (main entry point)
├── optimizer.py            # OR-Tools MIP berth scheduling engine
├── congestion.py           # Analytical congestion scoring engine
├── scenario_engine.py      # What-if scenario evaluation engine
├── generate_data.py        # Simulated vessel/berth data generator
├── run_optimizer.py        # CLI: run optimizer and validate schedule
├── requirements.txt        # Python dependencies
├── setup.sh                # One-line setup script
├── src/
│   └── ai_copilot.py       # AI Operations Copilot module
├── data/
│   ├── vessels.csv         # 15 simulated vessels
│   ├── berths.csv          # 5 simulated berths
│   └── schedule_output.csv # Pre-computed optimizer schedule
├── test_optimizer.py       # Optimizer tests
├── test_congestion.py      # Congestion engine tests
├── test_scenario_engine.py # Scenario engine tests (11 test groups)
├── test_ai_copilot.py      # AI Copilot tests (9 test groups, 100 checks)
└── docs/
    ├── architecture.md     # System architecture
    ├── setup-guide.md      # Detailed setup instructions
    ├── problem-statement.md
    └── solution-overview.md
```

---

## ⚡ How to Run

### Prerequisites

- Python 3.10 or later
- No API keys, no cloud accounts, no external services required

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Mitmahant/bob-ai-hackathon-PortVector.git
cd bob-ai-hackathon-PortVector

# 2. Install dependencies
pip install -r requirements.txt
# or use the setup script:
bash setup.sh
```

### Launch the Dashboard

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

The dashboard will:

1. Load the pre-computed optimizer schedule (`data/schedule_output.csv`)
2. Run the congestion engine on startup
3. Display the full 72-hour operational picture
4. Allow scenario selection via the sidebar controls
5. Show the AI Operations Copilot panel with live insights

### Regenerate Data (Optional)

The `data/` files are pre-committed and ready to use. To regenerate from scratch:

```bash
python generate_data.py     # regenerates vessels.csv and berths.csv
python run_optimizer.py     # re-runs optimizer, regenerates schedule_output.csv
streamlit run app.py        # launch dashboard
```

---

## 🧪 Running Tests

```bash
# All individual test suites
python test_optimizer.py
python test_congestion.py
python test_scenario_engine.py
python test_ai_copilot.py

# Optimizer + schedule validation
python run_optimizer.py
```

All test suites use a custom assertion harness and exit with code 1 on failure.

---

## 🤖 AI Operations Copilot

The AI Copilot is a **deterministic rule-based decision-support layer**.

**What it is:**

- A downstream interpreter of structured engine outputs
- Produces: operational status summary, bottleneck analysis, priority actions with evidence, scenario comparison insights, bottleneck-shift warnings
- All stated facts are derived directly from the optimizer and congestion engine — no values are fabricated

**What it is NOT:**

- An LLM or generative AI model
- Connected to an external API or internet service
- Performing independent numerical calculation
- Claiming to predict real-world port conditions

The copilot is architected so that a real LLM can be substituted for the template-based generators (in `src/ai_copilot.py`) without modifying the dashboard or the calling interface.

The UI clearly distinguishes **✓ Calculated Facts** (green badge) from **🤖 AI Decision-Support Recommendations** (blue badge).

---

## 📊 Dashboard Sections

1. **72-Hour Operational Snapshot** — KPI cards: congestion score, vessels scheduled, average wait, total demurrage, service hours
2. **Port Congestion — Berth Rankings** — per-berth congestion scores with badges, progress bars, and bottleneck indicator
3. **Berth Utilization** — bar chart comparing all berths, color-coded by congestion level
4. **72-Hour Operational Plan** — Gantt chart of the optimizer-generated schedule (waiting + service)
5. **What-If Scenario Controls** — interactive service-time reduction (10–30%), affected vessel table
6. **Baseline vs Scenario Comparison** — detailed metric table with delta indicators
7. **Modeled Scenario Impact** — impact cards showing savings vs baseline
8. **Berth 3 Queue Comparison** — side-by-side Gantt for baseline vs scenario
9. **Operational Analysis** — deterministic bottleneck explanation and scenario narrative
10. **🤖 AI Operations Copilot** — operational status, bottleneck analysis, priority actions, scenario insight, bottleneck-shift warning
11. **Full Optimizer Schedule** — expandable vessel detail table
12. **Data & Methodology** — transparency panel with formulas, limitations, and disclaimer

---

## 🖥️ Demo

| Artifact         | Link                                                    |
| ---------------- | ------------------------------------------------------- |
| 📹 Demo Video    | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo     | [See demo/live-demo-url.txt](demo/live-demo-url.txt)     |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/)               |
| 📊 Presentation  | [presentation/slides.pdf](presentation/slides.pdf)       |

---

## ⚠️ Known Limitations

- **Simulated data only** — no live port data feed; all vessel and berth data is generated for demo purposes
- **Crane scheduling not modelled** — crane data fields exist but are not used in optimization
- **Deterministic arrivals** — no stochastic delay model; vessel ETAs are fixed
- **Rule-based AI Copilot** — not LLM-powered; recommendations follow deterministic rules
- **Tide and weather not modelled** — planning horizon assumes constant operating conditions
- **72-hour horizon** — the optimizer is not designed for multi-day rolling horizons

---

## 🏅 What We're Most Proud Of

The cleanest architectural achievement is the strict separation between the numerical engines and the AI layer: the optimizer, congestion engine, and scenario engine are immutable sources of truth, and the AI Copilot only reads their outputs — it cannot invent, modify, or override a single number. This architecture is validated by a dedicated 100-check test suite that verifies every AI-stated value traces to an actual engine calculation.

The bottleneck-shift detection (Berth 3 → Berth 2 after a service-time intervention) is a particularly compelling AI insight: it warns operators that relieving one constrained resource exposes the next, which is exactly the kind of non-obvious operational consequence that decision-support AI should surface.
