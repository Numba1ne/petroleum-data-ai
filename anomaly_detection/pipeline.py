"""
End-to-end anomaly detection pipeline.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from anomaly_detection.utils import load_daily_data, get_well_data
from anomaly_detection.detectors import (
    combined_statistical_anomalies,
    decline_residual_anomalies,
)
from anomaly_detection.scoring import (
    assign_severity,
    compute_anomaly_score,
    summarise_well_anomalies,
)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "anomalies"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def detect_well_anomalies(
    well: str,
    df: Optional[pd.DataFrame] = None,
    include_residual: bool = True,
) -> pd.DataFrame:
    """
    Run all detectors on one well and return a flagged DataFrame.
    """
    if df is None:
        df = load_daily_data()

    well_df = get_well_data(df, well)

    # Keep well name available for residual detector if needed
    well_df = well_df.copy()
    well_df["well_bore_code"] = well

    flags = combined_statistical_anomalies(well_df)

    if include_residual:
        flags["decline_residual_anomaly"] = decline_residual_anomalies(well_df)
        flags["any_anomaly"] = (
            flags["any_anomaly"] | flags["decline_residual_anomaly"]
        )

    flags["anomaly_score"] = compute_anomaly_score(flags)
    flags["severity"] = flags["anomaly_score"].apply(assign_severity)

    # Attach useful production columns for later analysis / dashboard
    flags["bore_oil_vol"] = well_df["bore_oil_vol"]
    flags["water_cut"] = well_df.get("water_cut")
    flags["gor"] = well_df.get("gor")
    flags["well_bore_code"] = well

    return flags


def run_anomaly_pipeline(
    wells: Optional[List[str]] = None,
    include_residual: bool = True,
    save: bool = True,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Run anomaly detection for multiple wells.
    Returns a dict of {well: flags_df} plus a summary DataFrame,
    and optionally saves CSVs + summary.
    """
    df = load_daily_data()

    if wells is None:
        wells = sorted(df["well_bore_code"].unique())

    results = {}
    summaries = []

    for well in wells:
        print(f"Detecting anomalies for {well} ...")
        flags = detect_well_anomalies(well, df=df, include_residual=include_residual)
        results[well] = flags

        summary = summarise_well_anomalies(flags, well)
        summaries.append(summary)

        if save:
            safe_name = well.replace("/", "").replace(" ", "")
            flags.to_csv(OUTPUT_DIR / f"{safe_name}_anomalies.csv")

    summary_df = pd.DataFrame(summaries)
    summary_df = summary_df.sort_values("anomaly_pct", ascending=False).reset_index(drop=True)

    if save:
        summary_df.to_csv(OUTPUT_DIR / "anomaly_summary.csv", index=False)
        print(f"\nSummary saved to {OUTPUT_DIR / 'anomaly_summary.csv'}")

    return results, summary_df
