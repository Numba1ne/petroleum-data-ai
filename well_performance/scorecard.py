"""
Well Performance Scorecard
Ranks producer wells on production, water cut, anomalies, and decline health.
"""

from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from well_performance.utils import load_producer_df
from anomaly_detection.pipeline import detect_well_anomalies
from forecasting.forecast import forecast_well
from forecasting.evaluate import evaluate_forecast

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "scorecard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_well_metrics(well: str, df: pd.DataFrame) -> Dict:
    """Compute core performance metrics for one well."""
    well_df = df[df["well_bore_code"] == well].copy()
    well_df = well_df.sort_values("dateprd")

    if well_df.empty:
        return {"well": well, "error": "No data"}

    # Production metrics
    cum_oil = well_df["bore_oil_vol"].sum()
    cum_water = well_df["bore_wat_vol"].sum()
    cum_liquid = cum_oil + cum_water
    avg_water_cut = (cum_water / cum_liquid) if cum_liquid > 0 else np.nan

    # Recent performance (last 90 days)
    cutoff = well_df["dateprd"].max() - pd.Timedelta(days=90)
    recent = well_df[well_df["dateprd"] >= cutoff]
    recent_oil_rate = recent["bore_oil_vol"].mean() if len(recent) > 0 else np.nan
    recent_water_cut = recent["water_cut"].mean() if len(recent) > 0 else np.nan

    # Water cut trend (recent - early)
    early = well_df.head(max(30, len(well_df) // 5))
    early_wc = early["water_cut"].mean() if len(early) > 0 else np.nan
    wc_trend = (
        (recent_water_cut - early_wc)
        if pd.notna(recent_water_cut) and pd.notna(early_wc)
        else np.nan
    )

    # Anomaly burden
    try:
        flags = detect_well_anomalies(well, include_residual=True)
        anomaly_pct = flags["any_anomaly"].mean() * 100
        max_score = flags["anomaly_score"].max()
    except Exception:
        anomaly_pct = np.nan
        max_score = np.nan

    # Decline health
    try:
        result = forecast_well(well, forecast_days=30, train_frac=0.85)
        metrics = evaluate_forecast(result)
        r2 = metrics.get("r2_train", np.nan)
        mape = metrics.get("mape_test", np.nan)
    except Exception:
        r2 = np.nan
        mape = np.nan

    return {
        "well": well,
        "cum_oil": cum_oil,
        "recent_oil_rate": recent_oil_rate,
        "avg_water_cut": avg_water_cut,
        "recent_water_cut": recent_water_cut,
        "wc_trend": wc_trend,
        "anomaly_pct": anomaly_pct,
        "max_anomaly_score": max_score,
        "decline_r2": r2,
        "forecast_mape": mape,
        "days_on": len(well_df),
    }


def score_wells(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert metrics into 0-100 component scores and an overall score.
    Higher overall = better performance / healthier well.
    """
    df = metrics_df.copy()

    def minmax(series, higher_is_better=True):
        s = series.astype(float)
        mn, mx = s.min(), s.max()
        if pd.isna(mn) or pd.isna(mx) or mx == mn:
            return pd.Series(50.0, index=s.index)
        norm = (s - mn) / (mx - mn)
        if not higher_is_better:
            norm = 1 - norm
        return norm * 100

    df["score_oil"] = minmax(df["cum_oil"], higher_is_better=True)
    df["score_recent_rate"] = minmax(df["recent_oil_rate"], higher_is_better=True)
    df["score_water_cut"] = minmax(df["recent_water_cut"], higher_is_better=False)
    df["score_anomaly"] = minmax(df["anomaly_pct"], higher_is_better=False)
    df["score_decline"] = minmax(df["decline_r2"], higher_is_better=True)

    # Weighted overall score
    df["overall_score"] = (
        0.30 * df["score_oil"]
        + 0.20 * df["score_recent_rate"]
        + 0.20 * df["score_water_cut"]
        + 0.15 * df["score_anomaly"]
        + 0.15 * df["score_decline"]
    )

    df = df.sort_values("overall_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def build_scorecard(
    wells: Optional[List[str]] = None,
    save: bool = True,
) -> pd.DataFrame:
    """Build the full performance scorecard."""
    df = load_producer_df()
    if wells is None:
        wells = sorted(df["well_bore_code"].unique())

    rows = []
    for well in wells:
        print(f"Scoring {well} ...")
        rows.append(compute_well_metrics(well, df))

    metrics_df = pd.DataFrame(rows)
    scorecard = score_wells(metrics_df)

    if save:
        scorecard.to_csv(OUTPUT_DIR / "well_performance_scorecard.csv", index=False)
        print(f"Saved to {OUTPUT_DIR / 'well_performance_scorecard.csv'}")

    return scorecard
