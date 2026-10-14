from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

# Project root is two levels up from this file
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"


# @st.cache_data  # We'll import streamlit later - temporary note
def load_daily_production():
    """Load cleaned daily production data from SQLite."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run the Project 1 pipeline first: python src/pipeline/clean_data.py"
        )

    engine = create_engine(f"sqlite:///{DB_PATH}")
    df = pd.read_sql("SELECT * FROM daily_production", engine)
    # Ensure date is datetime
    if "dateprd" in df.columns:
        df["dateprd"] = pd.to_datetime(df["dateprd"])

    return df
