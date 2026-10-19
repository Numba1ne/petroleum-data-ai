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
    result["any_anomaly"] = (
        result["oil_zscore_anomaly"]
        | result["oil_rate_change_anomaly"]
        | result["water_cut_jump_anomaly"]
    )

    return result
