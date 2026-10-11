"""
Volve Production Data – Cleaning & Feature Engineering Pipeline
===============================================================

Processes both the Daily and Monthly sheets from the raw Excel workbook,
applying the following cleaning steps:

Daily sheet
-----------
  1. Standardise column names (snake_case, strip special chars).
  2. Parse date column to datetime.
  3. Flag negative volume values as NaN (and count them for QC).
  4. Impute pressure / temperature columns per-well with a rolling mean,
     then forward-fill, then backward-fill any remaining gaps.
  5. Leave volume columns (oil, gas, water, wi) as-is for zeros
     (a zero on a valid day means the well was shut-in, which is real data).
  6. Assign a time-aware well_type per row: INJECTOR when bore_wi_vol > 0,
     PRODUCER otherwise.  This allows wells that switch roles over time to
     be handled correctly.
  7. Calculate derived metrics with safe division:
       • water_cut   = bore_wat_vol / (bore_oil_vol + bore_wat_vol)
       • gor         = bore_gas_vol / bore_oil_vol
       • onstream_efficiency = on_stream_hrs / 24
     Both water_cut and gor are set to NaN (not 0) when denominators are 0.

Monthly sheet
-------------
  Same column standardisation + date parsing + negative-volume flagging.
  Written to separate CSV / Parquet / SQLite table.

Outputs
-------
  data/processed/daily_production_clean.{csv,parquet}
  data/processed/monthly_production_clean.{csv,parquet}
  data/db/volve_production.db   (tables: daily_production, monthly_production)
  reports/data_quality_report.md

Usage
-----
    python src/pipeline/clean_data.py
    python src/pipeline/clean_data.py --input data/raw/custom_file.xlsx
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# ---------------------------------------------------------------------------
# Resolve project root so this script works whether called from repo root or
# from the src/pipeline/ sub-directory.
# ---------------------------------------------------------------------------
_PIPELINE_DIR = Path(__file__).resolve().parent
_SRC_DIR      = _PIPELINE_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from config import (  # noqa: E402
    BASE_DIR,
    CLAMP_NEGATIVE_VOLUMES,
    DAILY_CSV,
    DAILY_PARQUET,
    DB_PATH,
    MONTHLY_CSV,
    MONTHLY_PARQUET,
    PROCESSED_DIR,
    DB_DIR,
    QUALITY_REPORT_PATH,
    RAW_EXCEL_PATH,
    REPORT_DIR,
    ROLLING_IMPUTE_COLS,
    ROLLING_WINDOW,
    SHEET_DAILY,
    SHEET_MONTHLY,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case, snake_case, strip special characters."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def _clamp_negative_volumes(df: pd.DataFrame, vol_cols: list[str]) -> tuple[pd.DataFrame, dict]:
    """Replace negative values in volume columns with NaN; return counts."""
    neg_counts: dict[str, int] = {}
    for col in vol_cols:
        if col not in df.columns:
            continue
        mask = df[col] < 0
        neg_counts[col] = int(mask.sum())
        if CLAMP_NEGATIVE_VOLUMES and mask.any():
            df.loc[mask, col] = np.nan
    return df, neg_counts


def _impute_pressure_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Per-well imputation for sensor readings:
      rolling mean (window=ROLLING_WINDOW) → forward-fill → backward-fill.
    This order means we prefer nearby values, then propagate forward,
    then fill leading NaNs with the first available reading.
    """
    present_cols = [c for c in cols if c in df.columns]
    if not present_cols:
        return df

    def _fill(group: pd.Series) -> pd.Series:
        rolled = group.rolling(ROLLING_WINDOW, min_periods=1).mean()
        return rolled.ffill().bfill()

    for col in present_cols:
        df[col] = (
            df.groupby("well_bore_code", group_keys=False)[col]
            .transform(_fill)
        )
    return df


def _well_type_per_row(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign well_type per row so wells that switch roles are handled correctly:
      • INJECTOR  – when bore_wi_vol is > 0 on that specific day
      • PRODUCER  – otherwise (including shut-in days with zero production)
    """
    if "bore_wi_vol" in df.columns:
        df["well_type"] = np.where(
            df["bore_wi_vol"].fillna(0) > 0, "INJECTOR", "PRODUCER"
        )
    else:
        df["well_type"] = "UNKNOWN"
    return df


def _derive_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate water cut, GOR, and on-stream efficiency with safe division."""

    # Water cut – NaN when both oil and water are zero or missing
    liq = df.get("bore_oil_vol", pd.Series(np.nan, index=df.index)).fillna(0) \
          + df.get("bore_wat_vol", pd.Series(np.nan, index=df.index)).fillna(0)
    df["water_cut"] = np.where(
        liq > 0,
        df.get("bore_wat_vol", np.nan) / liq,
        np.nan,
    )

    # GOR – NaN when oil is zero or missing
    df["gor"] = np.where(
        df.get("bore_oil_vol", pd.Series(0, index=df.index)).fillna(0) > 0,
        df.get("bore_gas_vol", np.nan) / df["bore_oil_vol"],
        np.nan,
    )

    # On-stream efficiency – fraction of day the well was producing
    if "on_stream_hrs" in df.columns:
        df["onstream_efficiency"] = (df["on_stream_hrs"] / 24).clip(0, 1)

    return df


# ---------------------------------------------------------------------------
# QC report builder
# ---------------------------------------------------------------------------

class QualityReport:
    """Accumulates quality notes and writes a Markdown report."""

    def __init__(self) -> None:
        self._sections: list[str] = []

    def add(self, text: str) -> None:
        self._sections.append(text)

    def add_heading(self, text: str, level: int = 2) -> None:
        prefix = "#" * level
        self._sections.append(f"\n{prefix} {text}\n")

    def add_df(self, df: pd.DataFrame) -> None:
        self._sections.append(df.to_markdown() if hasattr(df, "to_markdown") else str(df))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Volve Production Data – Quality Report\n\n")
            f.write("\n".join(self._sections))
        log.info("Quality report → %s", path)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_excel(raw_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not raw_path.exists():
        log.error("Raw data file not found: %s", raw_path)
        log.error("Run  python src/pipeline/download_kaggle_data.py  first.")
        sys.exit(1)

    log.info("Loading '%s' …", SHEET_DAILY)
    daily = pd.read_excel(raw_path, sheet_name=SHEET_DAILY)
    log.info("Loading '%s' …", SHEET_MONTHLY)
    monthly = pd.read_excel(raw_path, sheet_name=SHEET_MONTHLY)
    log.info("Raw daily:   %d rows × %d cols", *daily.shape)
    log.info("Raw monthly: %d rows × %d cols", *monthly.shape)
    return daily, monthly


# ---------------------------------------------------------------------------
# Daily cleaning
# ---------------------------------------------------------------------------

def clean_daily(raw: pd.DataFrame, qr: QualityReport) -> pd.DataFrame:
    df = raw.copy()

    # 1. Column names
    df = _standardise_columns(df)

    # 2. Date
    df["dateprd"] = pd.to_datetime(df["dateprd"], errors="coerce")
    df = df.sort_values(["well_bore_code", "dateprd"]).reset_index(drop=True)

    qr.add_heading("Daily – Overview", 2)
    qr.add(f"- **Shape (raw):** {raw.shape}")
    qr.add(f"- **Date range:** {df['dateprd'].min().date()} → {df['dateprd'].max().date()}")
    qr.add(f"- **Unique wells:** {df['well_bore_code'].nunique()}")

    # 3. Missing values – BEFORE
    missing_before = df.isna().sum()
    missing_before = missing_before[missing_before > 0].rename("missing_before")

    # 4. Negative volumes
    vol_cols_present = [c for c in
        ["bore_oil_vol", "bore_gas_vol", "bore_wat_vol", "bore_wi_vol"]
        if c in df.columns]
    df, neg_counts = _clamp_negative_volumes(df, vol_cols_present)

    qr.add_heading("Negative Volume Counts (clamped to NaN)", 3)
    neg_series = pd.Series(neg_counts)
    neg_with_values = neg_series[neg_series > 0]
    if neg_with_values.empty:
        qr.add("_No negative volume values found._")
    else:
        for col, cnt in neg_with_values.items():
            qr.add(f"- **{col}:** {cnt:,} negative rows clamped to NaN")

    # 5. Impute sensor columns
    df = _impute_pressure_cols(df, ROLLING_IMPUTE_COLS)

    # 6. Well type (time-aware per row)
    df = _well_type_per_row(df)

    # 7. Derived metrics
    df = _derive_metrics(df)

    # Missing values – AFTER
    missing_after = df.isna().sum()
    missing_after = missing_after[missing_after > 0].rename("missing_after")
    comparison = pd.concat([missing_before, missing_after], axis=1).fillna(0).astype(int)
    comparison = comparison[comparison.sum(axis=1) > 0]

    qr.add_heading("Missing Values: Before vs After Imputation", 3)
    qr.add_df(comparison)

    # Missing % by well for key volume columns
    qr.add_heading("Missing % by Well (Volume Columns)", 3)
    for col in vol_cols_present:
        miss_by_well = (
            df.groupby("well_bore_code")[col]
            .apply(lambda s: 100 * s.isna().sum() / len(s))
            .rename(f"{col}_missing_%")
            .round(1)
        )
        qr.add(f"\n**{col}**\n")
        qr.add_df(miss_by_well.reset_index())

    # Completeness over time
    qr.add_heading("Monthly Data Completeness (daily oil vol)", 3)
    if "bore_oil_vol" in df.columns:
        monthly_completeness = (
            df.assign(month=df["dateprd"].dt.to_period("M"))
            .groupby("month")["bore_oil_vol"]
            .apply(lambda s: round(100 * s.notna().sum() / len(s), 1))
            .reset_index(name="completeness_%")
        )
        qr.add_df(monthly_completeness.tail(24))

    # Outlier summary
    qr.add_heading("Summary Statistics (Daily, cleaned)", 3)
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    qr.add_df(df[num_cols].describe().round(2))

    log.info("Daily clean complete: %d rows × %d cols", *df.shape)
    return df


# ---------------------------------------------------------------------------
# Monthly cleaning
# ---------------------------------------------------------------------------

def clean_monthly(raw: pd.DataFrame, qr: QualityReport) -> pd.DataFrame:
    df = raw.copy()
    df = _standardise_columns(df)

    # The monthly sheet has a rogue row 0 that contains unit labels (Sm3, hrs, etc.)
    # Drop any row where the wellbore name column is NaN (unit header rows).
    wellbore_col = next(
        (c for c in df.columns if "wellbore" in c or "well_bore" in c or "well" in c),
        None,
    )
    if wellbore_col:
        df = df[df[wellbore_col].notna()].copy()

    # Coerce all columns that should be numeric
    numeric_candidates = [c for c in df.columns
                          if c not in (wellbore_col or "", "npd_facility_name", "flow_kind")]
    for col in numeric_candidates:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Build a proper date from Year + Month integer columns (no single date col exists)
    if "year" in df.columns and "month" in df.columns:
        df["date"] = pd.to_datetime(
            df["year"].astype(int).astype(str) + "-"
            + df["month"].astype(int).astype(str) + "-01",
            errors="coerce",
        )

    # Sort
    sort_cols = [c for c in [wellbore_col, "date"] if c and c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)

    # Negative volumes (column names may differ from daily — use actual names)
    vol_cols_present = [c for c in df.columns
                        if any(v in c for v in ["oil", "gas", "wat", "water", "wi"])
                        and df[c].dtype in [float, "float64"]]
    df, neg_counts = _clamp_negative_volumes(df, vol_cols_present)

    df = df.reset_index(drop=True)

    qr.add_heading("Monthly – Overview", 2)
    qr.add(f"- **Shape (raw):** {raw.shape}")
    qr.add(f"- **Columns:** {list(df.columns)}")
    neg_with_values = {k: v for k, v in neg_counts.items() if v > 0}
    if neg_with_values:
        qr.add(f"- **Negative volumes clamped:** {neg_with_values}")

    qr.add_heading("Summary Statistics (Monthly, cleaned)", 3)
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    if num_cols:
        qr.add_df(df[num_cols].describe().round(2))

    log.info("Monthly clean complete: %d rows × %d cols", *df.shape)
    return df


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_outputs(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    qr: QualityReport,
) -> None:
    # Ensure directories exist
    for d in [PROCESSED_DIR, DB_DIR, REPORT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # CSV + Parquet
    daily.to_csv(DAILY_CSV, index=False)
    daily.to_parquet(DAILY_PARQUET, index=False)
    log.info("Daily CSV     -> %s", DAILY_CSV)
    log.info("Daily Parquet -> %s", DAILY_PARQUET)

    monthly.to_csv(MONTHLY_CSV, index=False)
    monthly.to_parquet(MONTHLY_PARQUET, index=False)
    log.info("Monthly CSV     -> %s", MONTHLY_CSV)
    log.info("Monthly Parquet -> %s", MONTHLY_PARQUET)

    # SQLite
    engine = create_engine(f"sqlite:///{DB_PATH}")
    with engine.begin() as conn:
        daily.to_sql("daily_production", conn, if_exists="replace", index=False)
        monthly.to_sql("monthly_production", conn, if_exists="replace", index=False)
    log.info("Database -> %s", DB_PATH)

    # Quality report
    qr.write(QUALITY_REPORT_PATH)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(raw_path: Path | None = None) -> None:
    path = raw_path or RAW_EXCEL_PATH
    qr = QualityReport()

    daily_raw, monthly_raw = load_excel(path)

    daily_clean   = clean_daily(daily_raw, qr)
    monthly_clean = clean_monthly(monthly_raw, qr)

    save_outputs(daily_clean, monthly_clean, qr)

    log.info("Pipeline complete [OK]")
    log.info("  Daily:   %d rows", len(daily_clean))
    log.info("  Monthly: %d rows", len(monthly_clean))
    log.info("  DB:      %s", DB_PATH)
    log.info("  Report:  %s", QUALITY_REPORT_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean and store Volve production data.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=f"Path to raw Excel file (default: {RAW_EXCEL_PATH})",
    )
    args = parser.parse_args()
    main(args.input)