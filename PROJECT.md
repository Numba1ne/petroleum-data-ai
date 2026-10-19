# Petroleum Data AI – Volve Field Analytics

**Role:** Solo builder
**Stack:** Python, Pandas, SQLite, Streamlit, Plotly, SciPy, OpenAI
**Dataset:** Equinor Volve production data (public)

## Problem

Upstream teams deal with messy production data, slow reporting, and fragmented tools for forecasting and well surveillance. I wanted to build a single, end-to-end system that goes from raw field data to interactive analysis and natural-language answers.

## What I built

A progressive analytics toolkit with six connected layers:

1. **Data pipeline** – Download, clean, and validate daily/monthly production; derive water cut, GOR, and well type; store in SQLite with automated QC reporting.
2. **Interactive dashboard** – Streamlit app with filters (producer/injector, wells, dates), KPIs, production charts, and diagnostic views (water cut & GOR).
3. **Decline-curve forecasting** – Arps exponential and hyperbolic models with peak-rate alignment, train/test evaluation (R², MAPE, RMSE), and future rate forecasts.
4. **Anomaly detection** – Rolling z-score, rate-change, water-cut jump, and decline-residual detectors, plus severity scoring.
5. **Well performance scorecard** – Composite ranking from cumulative oil, recent rate, water cut, anomaly burden, and decline health.
6. **AI assistant** – Tool-calling agent that answers questions like "Forecast F-12 H for 180 days" or "Which wells look unhealthy?" by invoking the modules above.

## Technical highlights

- Clean modular design: each project is a reusable package (`forecasting`, `anomaly_detection`, `well_performance`, `ai_agent`).
- Time-aware well typing and shut-in-aware filtering for more realistic decline fits.
- Residual anomalies link forecasting and surveillance (actual vs expected decline).
- LLM agent uses structured tools instead of hallucinating numbers.

## Results

- Working dashboard with production, diagnostics, forecast, anomaly, scorecard, and chat tabs.
- Decline fits with strong R² on main producers (e.g. F-12 H improved after peak-rate alignment).
- Anomaly pipeline flags operational and reservoir events with multi-detector scoring.
- AI agent returns data-backed answers via real analytical tools.

## Why it matters

The project mirrors real petroleum workflows — data quality, surveillance, forecasting, and decision support — while staying portfolio-friendly and fully reproducible on public Volve data.

**Repo:** https://github.com/Numba1ne/petroleum-data-ai

---

## Shorter LinkedIn version

Built an end-to-end petroleum analytics system on the Equinor Volve dataset:

- ETL pipeline → clean SQLite production database
- Streamlit dashboard (KPIs, diagnostics, rankings)
- Arps decline-curve forecasting with evaluation
- Multi-detector anomaly detection + severity scores
- Well performance scorecard
- AI assistant that answers production questions using real tools

**Stack:** Python, Pandas, Streamlit, Plotly, SciPy, OpenAI
**Repo:** github.com/Numba1ne/petroleum-data-ai
