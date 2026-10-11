"""
Central configuration for the Volve production data pipeline.

All path and dataset constants live here so that every script imports
from one place. Adjust DATASET_SLUG or file names here if the source
ever changes.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Repository root (two levels up from src/config.py)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
RAW_DIR       = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_DIR        = BASE_DIR / "data" / "db"
REPORT_DIR    = BASE_DIR / "reports"

# ---------------------------------------------------------------------------
# File names
# ---------------------------------------------------------------------------
RAW_EXCEL_FILE      = "Volve production data.xlsx"
RAW_EXCEL_PATH      = RAW_DIR / RAW_EXCEL_FILE
DAILY_CSV           = PROCESSED_DIR / "daily_production_clean.csv"
DAILY_PARQUET       = PROCESSED_DIR / "daily_production_clean.parquet"
MONTHLY_CSV         = PROCESSED_DIR / "monthly_production_clean.csv"
MONTHLY_PARQUET     = PROCESSED_DIR / "monthly_production_clean.parquet"
DB_PATH             = DB_DIR / "volve_production.db"
QUALITY_REPORT_PATH = REPORT_DIR / "data_quality_report.md"

# ---------------------------------------------------------------------------
# Kaggle dataset
# ---------------------------------------------------------------------------
DATASET_SLUG        = "lamyalbert/volve-production-data"

# ---------------------------------------------------------------------------
# Sheet names inside the Excel workbook
# ---------------------------------------------------------------------------
SHEET_DAILY   = "Daily Production Data"
SHEET_MONTHLY = "Monthly Production Data"

# ---------------------------------------------------------------------------
# Cleaning thresholds
# ---------------------------------------------------------------------------
# Columns whose missing values are imputed with per-well rolling averages.
# These are continuous sensor readings where interpolation makes physical sense.
# Names must match the standardised column names produced by _standardise_columns().
# Verified against actual Volve Excel output (2026-10-11).
ROLLING_IMPUTE_COLS = [
    "avg_downhole_pressure",    # downhole gauge pressure
    "avg_downhole_temperature", # downhole temperature
    "dp_choke_size",            # choke size differential pressure
    "avg_choke_size_p",         # choke size (production)
    "avg_annulus_press",        # annulus pressure
    "avg_whp_p",                # wellhead pressure (production)
    "avg_wht_p",                # wellhead temperature (production)
    "avg_dp_tubing",            # tubing differential pressure
]
ROLLING_WINDOW = 7       # days

# Volume columns — zeros are valid (well shut-in); negatives are anomalies.
VOLUME_COLS = [
    "bore_oil_vol",
    "bore_gas_vol",
    "bore_wat_vol",
    "bore_wi_vol",
    "flow_kind",          # category, handled separately
]

# Clamp negative volumes to NaN (they will be reported in QC, not silently dropped)
CLAMP_NEGATIVE_VOLUMES = True
