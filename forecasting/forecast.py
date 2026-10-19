"""
Production Forecasting Pipeline
Fits decline curves and generates future production forecasts.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from forecasting.utils import load_producer_data, get_well_series
from forecasting.decline_curves import (
    select_best_model,
    exponential_decline,
    hyperbolic_decline,
    DeclineResult,
)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "forecasts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def prepare_time_arrays(
    series: pd.DataFrame,
    from_peak: bool = True,
) -> Tuple[np.ndarray, np.ndarray, pd.Timestamp]:
    """
    Convert a well series into t (days) and q (oil rate).
    Optionally start from the peak production rate, skipping the ramp-up
    period that would otherwise drag the decline fit down.
    """
    series = series.sort_index()

    if from_peak and len(series) > 10:
        # Start from the peak oil rate
        peak_idx = series["bore_oil_vol"].idxmax()
        series = series.loc[peak_idx:].copy()

    start_date = series.index[0]
    t = (series.index - start_date).days.values.astype(float)
    q = series["bore_oil_vol"].values.astype(float)
    return t, q, start_date


def generate_forecast(
    result: DeclineResult,
    t_hist: np.ndarray,
    start_date: pd.Timestamp,
    forecast_days: int = 365,
) -> pd.DataFrame:
    """
    Generate historical fit + future forecast.
    Returns a DataFrame with date, actual (NaN in future), predicted, and type.
    """
    t_future = np.arange(t_hist[-1] + 1, t_hist[-1] + 1 + forecast_days)
    t_all = np.concatenate([t_hist, t_future])

    if result.model == "exponential":
        q_pred = exponential_decline(t_all, result.qi, result.di)
    else:
        q_pred = hyperbolic_decline(t_all, result.qi, result.di, result.b)

    dates = start_date + pd.to_timedelta(t_all, unit="D")

    df = pd.DataFrame({
        "date": dates,
        "t_days": t_all,
        "predicted_oil": q_pred,
        "segment": ["history"] * len(t_hist) + ["forecast"] * len(t_future),
    })
    return df


def forecast_well(
    well: str,
    df: Optional[pd.DataFrame] = None,
    forecast_days: int = 365,
    train_frac: float = 0.8,
) -> Dict:
    """
    Full pipeline for one well:
    1. Split into train/test
    2. Fit best decline model on train
    3. Evaluate on test
    4. Generate future forecast
    """
    if df is None:
        df = load_producer_data()

    series = get_well_series(df, well)
    if len(series) < 30:
        return {"well": well, "error": "Insufficient data points (<30)"}

    t_all, q_all, start_date = prepare_time_arrays(series, from_peak=True)

    # Train / Test split
    split_idx = int(len(t_all) * train_frac)
    t_train, q_train = t_all[:split_idx], q_all[:split_idx]
    t_test, q_test = t_all[split_idx:], q_all[split_idx:]

    # Fit decline model on training set
    result = select_best_model(t_train, q_train)

    # Predict on test set
    if result.model == "exponential":
        q_test_pred = exponential_decline(t_test, result.qi, result.di)
    else:
        q_test_pred = hyperbolic_decline(t_test, result.qi, result.di, result.b)

    # Generate full forecast (history + future)
    forecast_df = generate_forecast(
        result, t_all, start_date, forecast_days=forecast_days
    )

    # Add actual historical oil to forecast_df for convenience
    actual_oil = np.full(len(forecast_df), np.nan)
    actual_oil[: len(q_all)] = q_all
    forecast_df["actual_oil"] = actual_oil

    return {
        "well": well,
        "model": result.model,
        "qi": result.qi,
        "di": result.di,
        "b": result.b,
        "r2_train": result.r2,
        "q_train": q_train,
        "q_test": q_test,
        "q_test_pred": q_test_pred,
        "forecast_df": forecast_df,
        "result": result,
    }


def run_all_wells(
    wells: Optional[List[str]] = None,
    forecast_days: int = 365,
    train_frac: float = 0.8,
) -> Dict[str, Dict]:
    """Run forecasting for multiple wells and save results."""
    df = load_producer_data()
    if wells is None:
        wells = sorted(df["well_bore_code"].unique())

    results = {}
    for well in wells:
        print(f"Forecasting {well} ...")
        res = forecast_well(
            well, df=df, forecast_days=forecast_days, train_frac=train_frac
        )
        results[well] = res

        # Save forecast CSV
        if "forecast_df" in res:
            clean_name = well.replace("/", "").replace(" ", "")
            out_path = OUTPUT_DIR / f"{clean_name}_forecast.csv"
            res["forecast_df"].to_csv(out_path, index=False)

    return results
