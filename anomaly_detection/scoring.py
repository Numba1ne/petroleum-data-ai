"""
Anomaly scoring utilities.
"""

import pandas as pd
from typing import Dict


def compute_anomaly_score(flags: pd.DataFrame) -> pd.Series:
    """
    Simple weighted anomaly score per day.
    Higher score = more severe / more detectors triggered.
    """
    weights = {
        "oil_zscore_anomaly": 1.0,
        "oil_rate_change_anomaly": 1.5,   # sudden changes are more important
        "water_cut_jump_anomaly": 2.0,    # water breakthrough is critical
        "decline_residual_anomaly": 1.8,  # deviation from expected decline
    }

    score = pd.Series(0.0, index=flags.index)

    for col, w in weights.items():
        if col in flags.columns:
            score += flags[col].astype(float) * w

    return score


def summarise_well_anomalies(flags: pd.DataFrame, well: str) -> Dict:
    """Create a short summary for one well."""
    total_days = len(flags)
    anomaly_days = int(flags["any_anomaly"].sum()) if "any_anomaly" in flags.columns else 0

    summary = {
        "well": well,
        "total_days": total_days,
        "anomaly_days": anomaly_days,
        "anomaly_pct": round(anomaly_days / total_days * 100, 2) if total_days > 0 else 0.0,
    }

    for col in ["oil_zscore_anomaly", "oil_rate_change_anomaly",
                "water_cut_jump_anomaly", "decline_residual_anomaly"]:
        if col in flags.columns:
            summary[col] = int(flags[col].sum())

    if "anomaly_score" in flags.columns:
        summary["max_score"] = float(flags["anomaly_score"].max())
        summary["mean_score"] = float(flags["anomaly_score"].mean())

    return summary
