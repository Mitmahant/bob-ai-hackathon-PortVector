# PortPulse AI — Live Demo Script
## IBM BoB AI Innovation Hackathon 2026 | Team Portvector

**Target duration:** 3–5 minutes  
**Application:** `streamlit run app.py` → http://localhost:8501  
**Data:** Simulated — 15 vessels, 5 berths, 72-hour horizon

---

## Before You Start

1. `pip install -r requirements.txt`
2. `streamlit run app.py`
3. Browser opens at http://localhost:8501
4. Confirm the dashboard loads with KPI cards visible at the top.

---

## Script

---

### [0:00 – 0:40] 1. Problem Introduction

> "Container ports operate reactively — berth bottlenecks are discovered only after
> vessels have already been waiting for hours, generating significant demurrage costs
> and supply-chain delays.
>
> PortPulse AI gives port planners a forward-looking 72-hour operational picture:
> an optimized berth schedule, transparent congestion scoring, what-if scenario
> modelling, and AI decision-support — all in a single dashboard, with no external
> API or cloud service required."

---

### [0:40 – 1:20] 2. Dashboard Overview & Baseline KPIs

**Action:** Point to the top of the dashboard.

> "The first section shows the 72-hour operational snapshot.
> Looking at the baseline KPIs:"

| KPI | Value |
|---|---|
| Vessels Scheduled | 15 / 15 |
| Total Wait Time | 39 h |
| Average Wait | 2.6 h |
| Maximum Wait | 16 h |
| Total Demurrage | $132,600 |
| Total Cost (Demurrage + Berth) | $192,900 |

> "These numbers come directly from the OR-Tools MIP optimizer —
> no values are fabricated."

---

### [1:20 – 1:50] 3. Berth 3 Bottleneck

**Action:** Scroll to the **Port Congestion — Berth Rankings** section.

> "The congestion engine scores every berth on utilization, queue depth,
> wait pressure, and throughput load.
>
> In the baseline, **Berth 3** is the primary bottleneck — it has the highest
> congestion index and is flagged with the bottleneck badge.
>
> This is why vessels are queuing and accumulating those 16 hours of maximum wait."

---

### [1:50 – 2:30] 4. Service-Time Reduction Scenario

**Action:** Use the sidebar controls — select **20% Service-Time Reduction** scenario.

> "Now let's model an operational intervention. I'll apply a 20% service-time
> reduction — representing faster crane cycles or improved berthing procedures.
>
> The scenario engine re-runs the optimizer on the modified inputs."

**Wait a moment for the scenario to apply, then scroll to the comparison table.**

> "Look at the impact:"

| Metric | Baseline | After 20% Reduction | Change |
|---|---|---|---|
| Total Wait | 39 h | 27 h | −12 h |
| Average Wait | 2.6 h | 1.8 h | −0.8 h |
| Maximum Wait | 16 h | 10 h | −6 h |
| Demurrage | $132,600 | $88,200 | −$44,400 |
| Berth Operating Cost | $60,300 | $53,100 | −$7,200 |
| **Total Cost** | **$192,900** | **$141,300** | **−$51,600** |

> "A 20% service-time improvement saves $51,600 in a single 72-hour window."

---

### [2:30 – 3:10] 5. AI Operations Copilot

**Action:** Scroll to the **AI Operations Copilot** panel.

> "The AI Operations Copilot interprets the engine outputs and generates
> structured decision support.
>
> It clearly distinguishes two types of output —
> the green badge marks **Calculated Facts** derived directly from the optimizer,
> and the blue badge marks **AI Decision-Support Recommendations** — interpretations
> and priority actions with evidence.
>
> Crucially, this is deterministic rule-based AI — no LLM, no external API.
> Every fact stated by the Copilot traces to an engine calculation.
> This is validated by a 100-check test suite."

---

### [3:10 – 3:40] 6. Bottleneck Shift: Berth 3 → Berth 2

**Action:** Scroll back to the congestion rankings (scenario view still active).

> "Here is the most operationally interesting insight.
>
> In the baseline, **Berth 3** was the bottleneck.
> After the service-time intervention, the bottleneck has **shifted to Berth 2**.
>
> The AI Copilot automatically detects and warns about this shift.
> This is exactly the kind of non-obvious operational consequence that
> decision-support AI should surface — relieving one constrained resource
> exposes the next."

---

### [3:40 – 4:10] 7. Gantt Chart & Methodology

**Action:** Scroll to the **72-Hour Operational Plan** Gantt chart.

> "The Gantt chart shows the full optimizer-generated schedule —
> waiting time in one colour, service time in another, across all 5 berths.
>
> At the bottom of the dashboard, the Data & Methodology panel shows
> all formulas used in the congestion scoring — full transparency, no black box."

---

### [4:10 – 4:30] 8. Closing Value Proposition

> "PortPulse AI demonstrates how a deterministic, explainable AI architecture
> can deliver real operational insight:
>
> — An OR-Tools MIP optimizer for provably optimal 72-hour berth scheduling  
> — Transparent congestion scoring with bottleneck identification  
> — What-if scenario modelling that quantifies intervention value  
> — A rule-based AI Copilot that grounds every recommendation in engine data  
>
> The architecture is designed so that a real LLM can be plugged in as
> the Copilot layer — without changing the optimizer, congestion engine,
> scenario engine, or dashboard.
>
> All data is simulated for demo purposes. No live port data, no external APIs."

---

## Key Numbers to Remember

| Fact | Value |
|---|---|
| Baseline bottleneck | Berth 3 |
| Scenario bottleneck | Berth 2 |
| Total cost saving (20% reduction) | −$51,600 |
| Demurrage saving | −$44,400 |
| Wait time reduction | −12 h |
| AI Copilot test checks | 100 |

---

## Notes for Presenter

- The application runs **entirely locally** — no internet required during demo.
- If the optimizer needs to be re-run: `python run_optimizer.py`
- All data is committed to the repository; the dashboard loads instantly.
- Do **not** claim live data, LLM functionality, or cloud deployment — none exist.
- The scenario sidebar slider defaults to 20% — confirm it matches before showing numbers.
