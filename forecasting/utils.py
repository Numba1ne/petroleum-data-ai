"""
Utility functions for production forecasting.
"""

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"


def load_producer_data(min_oil: float = 5.0) -> pd.DataFrame:
    """
    Load daily production data for producer wells only.
    Filters out near-zero production days (shut-in aware: drops noisy
    low-rate points that would distort the decline fit).
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run the Project 1 pipeline first."
        )

    engine = create_engine(f"sqlite:///{DB_PATH}")
    df = pd.read_sql(
        """
        SELECT dateprd, well_bore_code, bore_oil_vol, bore_gas_vol, bore_wat_vol,
               water_cut, gor, onstream_efficiency
        FROM daily_production
        WHERE well_type = 'PRODUCER'
        """,
        engine,
    )

    df["dateprd"] = pd.to_datetime(df["dateprd"])
    df = df.sort_values(["well_bore_code", "dateprd"]).reset_index(drop=True)

    # Keep only meaningful production days
    df = df[df["bore_oil_vol"] >= min_oil].copy()

    return df


def get_well_series(df: pd.DataFrame, well: str) -> pd.DataFrame:
    """Return a clean time series for a single well."""
    well_df = df[df["well_bore_code"] == well].copy()
    well_df = well_df.set_index("dateprd").sort_index()
    return well_df
