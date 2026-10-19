import os
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parents[1]

RAW_PATH = BASE_DIR / "data" / "raw" / "Volve production data.xlsx"
CSV_PATH = BASE_DIR / "data" / "processed" / "daily_production_clean.csv"
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"

# Data-dependent tests are skipped when the pipeline has not been run
# (e.g. in CI, where the raw Kaggle dataset is not available).
requires_raw = pytest.mark.skipif(
    not RAW_PATH.exists(), reason=f"Raw data not found at {RAW_PATH}"
)
requires_csv = pytest.mark.skipif(
    not CSV_PATH.exists(), reason=f"Cleaned CSV not found at {CSV_PATH}"
)
requires_db = pytest.mark.skipif(
    not DB_PATH.exists(), reason=f"Database not found at {DB_PATH}"
)


@requires_raw
def test_raw_data_exists():
    """Verify that raw Volve data exists."""
    assert os.path.exists(RAW_PATH), f"Raw data not found at {RAW_PATH}"


@requires_csv
def test_processed_data_exists():
    """Verify that cleaned CSV output exists."""
    assert os.path.exists(CSV_PATH), f"Cleaned CSV not found at {CSV_PATH}"


@requires_db
def test_database_tables():
    """Verify that database contains expected tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    conn.close()

    assert "daily_production" in tables, "Daily production table missing from database"


@requires_db
def test_no_empty_values_in_critical_columns():
    """Verify identifiers are complete and volumes are never negative."""
    engine = create_engine(f"sqlite:///{DB_PATH}")
    df = pd.read_sql(
        "SELECT well_bore_code, dateprd, bore_oil_vol FROM daily_production", engine
    )

    assert df["well_bore_code"].isna().sum() == 0, "Missing well IDs found"
    assert df["dateprd"].isna().sum() == 0, "Missing dates found"
    # bore_oil_vol may be null (injector wells / shut-in days); the pipeline
    # clamps negative volumes to NaN, so non-null values must be >= 0.
    oil = df["bore_oil_vol"].dropna()
    assert (oil >= 0).all(), "Negative oil volume measurements found"


# To run:
# pip install pytest
# pytest tests/test_data_quality.py -v
