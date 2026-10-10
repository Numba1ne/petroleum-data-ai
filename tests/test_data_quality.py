import os
import sqlite3
import pandas as pd
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

def test_raw_data_exists():
    """Verify that raw Volve data exists"""
    raw_path = BASE_DIR / "data" / "raw" / "Volve production data.xlsx"
    assert os.path.exists(raw_path), f"Raw data not found at {raw_path}"

def test_processed_data_exists():
    """Verify that cleaned CSV output exists"""
    csv_path = BASE_DIR / "data" / "processed" / "daily_production_clean.csv"
    assert os.path.exists(csv_path), f"Cleaned CSV not found at {csv_path}"

def test_database_tables():
    """Verify that database contains expected tables"""
    db_path = BASE_DIR / "data" / "db" / "volve_production.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    conn.close()
    
    assert "daily_production" in tables, "Daily production table missing from database"

def test_no_empty_values_in_critical_columns():
    """Verify critical columns have no missing values"""
    db_path = BASE_DIR / "data" / "db" / "volve_production.db"
    engine = create_engine(f"sqlite:///{db_path}")
    df = pd.read_sql("SELECT well_bore_code, dateprd, bore_oil_vol FROM daily_production", engine)
    
    assert df["well_bore_code"].isna().sum() == 0, "Missing well IDs found"
    assert df["dateprd"].isna().sum() == 0, "Missing dates found"
    assert df["bore_oil_vol"].isna().sum() == 0, "Missing oil volume measurements found"

# To run:
# pip install pytest
# pytest tests/test_data_quality.py -v