"""
Helpers for well performance scoring.
"""

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"


def load_producer_df() -> pd.DataFrame:
    """Load cleaned daily production for producers only."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    engine = create_engine(f"sqlite:///{DB_PATH}")
    df = pd.read_sql(
        """
        SELECT dateprd, well_bore_code, bore_oil_vol, bore_gas_vol,
               bore_wat_vol, water_cut, gor, onstream_efficiency
        FROM daily_production
        WHERE well_type = 'PRODUCER'
        """,
        engine,
    )
    df["dateprd"] = pd.to_datetime(df["dateprd"])
    return df.sort_values(["well_bore_code", "dateprd"]).reset_index(drop=True)
