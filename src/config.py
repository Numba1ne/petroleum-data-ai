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
ROLLING_IMPUTE_COLS = [
    "avg_downhole_pressure",
    "avg_downhole_temperature",
    "dp_choke_size",
    "avg_ann_a_pressure",
    "avg_ann_b_pressure",
    "avg_choke_size_p",
    "avg_wh_tubing_pressure",
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
