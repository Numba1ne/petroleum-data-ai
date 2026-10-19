"""
Utility functions for anomaly detection.
"""

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"


def load_daily_data(well_type: str = "PRODUCER") -> pd.DataFrame:
    """Load cleaned daily production data."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run Project 1 pipeline first."
        )

    engine = create_engine(f"sqlite:///{DB_PATH}")
    query = """
        SELECT dateprd, well_bore_code, well_type,
               bore_oil_vol, bore_gas_vol, bore_wat_vol,
               water_cut, gor, onstream_efficiency
        FROM daily_production
    """
    if well_type:
        query += f" WHERE well_type = '{well_type}'"

    df = pd.read_sql(query, engine)
    df["dateprd"] = pd.to_datetime(df["dateprd"])
    df = df.sort_values(["well_bore_code", "dateprd"]).reset_index(drop=True)
    return df


def get_well_data(df: pd.DataFrame, well: str) -> pd.DataFrame:
    """Return data for a single well, indexed by date."""
    well_df = df[df["well_bore_code"] == well].copy()
    well_df = well_df.set_index("dateprd").sort_index()
    return well_df
