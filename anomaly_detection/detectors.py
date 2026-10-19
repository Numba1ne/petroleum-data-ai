"""
Statistical and rule-based anomaly detectors.
"""

import numpy as np
import pandas as pd


def rolling_zscore(
    series: pd.Series,
    window: int = 30,
    threshold: float = 3.0,
) -> pd.Series:
    """
    Compute rolling z-score and return boolean mask of anomalies.
    """
    rolling_mean = series.rolling(window=window, min_periods=max(5, window // 3)).mean()
    rolling_std = series.rolling(window=window, min_periods=max(5, window // 3)).std()

    z = (series - rolling_mean) / rolling_std.replace(0, np.nan)
    anomalies = z.abs() > threshold
    return anomalies.fillna(False)


def rate_change_detector(
    series: pd.Series,
    window: int = 7,
    pct_threshold: float = 0.40,
) -> pd.Series:
    """
    Flag large percentage changes over a short window.
    Useful for sudden rate drops or spikes.
    """
    pct_change = series.pct_change(periods=window)
    anomalies = pct_change.abs() > pct_threshold
    return anomalies.fillna(False)


def water_cut_jump_detector(
    water_cut: pd.Series,
    window: int = 14,
    jump_threshold: float = 0.15,
) -> pd.Series:
    """
    Detect rapid increases in water cut (e.g. +15 percentage points in 14 days).
    """
    # water_cut is expected in fraction (0-1)
    change = water_cut - water_cut.shift(window)
    anomalies = change > jump_threshold
    return anomalies.fillna(False)


def combined_statistical_anomalies(
    well_df: pd.DataFrame,
    z_window: int = 30,
    z_threshold: float = 3.0,
    rate_window: int = 7,
    rate_pct: float = 0.40,
    wc_window: int = 14,
    wc_jump: float = 0.15,
) -> pd.DataFrame:
    """
    Run multiple detectors on a single well and return a DataFrame of flags.
    """
    result = pd.DataFrame(index=well_df.index)
    result["oil_zscore_anomaly"] = rolling_zscore(
        well_df["bore_oil_vol"], window=z_window, threshold=z_threshold
    )
    result["oil_rate_change_anomaly"] = rate_change_detector(
        well_df["bore_oil_vol"], window=rate_window, pct_threshold=rate_pct
    )

    if "water_cut" in well_df.columns:
        result["water_cut_jump_anomaly"] = water_cut_jump_detector(
            well_df["water_cut"], window=wc_window, jump_threshold=wc_jump
        )
    else:
        result["water_cut_jump_anomaly"] = False

    # Combined flag
    # (Residual anomalies are intentionally NOT included here — the pipeline
    # adds them via decline_residual_anomalies when include_residual=True.)
    result["any_anomaly"] = (
        result["oil_zscore_anomaly"]
        | result["oil_rate_change_anomaly"]
        | result["water_cut_jump_anomaly"]
    )

    return result


def decline_residual_anomalies(
    well_df: pd.DataFrame,
    residual_threshold: float = 2.5,
    min_points: int = 30,
) -> pd.Series:
    """
    Flag days where actual oil rate deviates strongly from the
    expected decline curve (from Project 3).
    """
    from forecasting.forecast import forecast_well

    anomalies = pd.Series(False, index=well_df.index)

    try:
        if "well_bore_code" not in well_df.columns:
            return anomalies
        well = well_df["well_bore_code"].iloc[0]

        # Rebuild a producer-style frame for forecast_well (it expects a
        # dateprd column and filters on well_bore_code itself).
        df_reset = well_df.reset_index()
        if "dateprd" not in df_reset.columns:
            # index had no name — first column holds the dates
            df_reset = df_reset.rename(columns={df_reset.columns[0]: "dateprd"})

        res = forecast_well(well, df=df_reset, forecast_days=0)
        if "error" in res or "forecast_df" not in res:
            return anomalies

        hist = res["forecast_df"]
        hist = hist[hist["segment"] == "history"].copy()

        # Shut-in aware: skip near-zero actuals that would distort residuals
        hist = hist[hist["actual_oil"].fillna(0) > 5]

        if len(hist) < min_points:
            return anomalies

        resid = hist["actual_oil"] - hist["predicted_oil"]
        std = resid.std()
        if not std or std == 0 or np.isnan(std):
            return anomalies

        resid_flags = resid.abs() > residual_threshold * std

        # Map back to original index
        for date, flag in zip(hist["date"], resid_flags):
            if bool(flag) and date in anomalies.index:
                anomalies.loc[date] = True

    except Exception:
        # If decline fit fails we simply return no residual flags
        pass

    return anomalies.fillna(False)
