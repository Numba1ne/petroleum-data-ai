from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine
import streamlit as st

# Project root is two levels up from this file
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"


@st.cache_data
def load_daily_production() -> pd.DataFrame:
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

    # Ensure numeric columns are properly typed
    numeric_cols = [
        "bore_oil_vol",
        "bore_gas_vol",
        "bore_wat_vol",
        "bore_wi_vol",
        "water_cut",
        "gor",
        "onstream_efficiency",
        "on_stream_hrs",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def compute_well_rankings(df: pd.DataFrame) -> pd.DataFrame:
    """Compute aggregate performance metrics and ranking by well."""
    records = []
    for well, group in df.groupby("well_bore_code"):
        oil = group["bore_oil_vol"].sum() if "bore_oil_vol" in group else 0.0
        gas = group["bore_gas_vol"].sum() if "bore_gas_vol" in group else 0.0
        wat = group["bore_wat_vol"].sum() if "bore_wat_vol" in group else 0.0
        wi = group["bore_wi_vol"].sum() if "bore_wi_vol" in group else 0.0
        liquid = oil + wat

        # Field water cut: Total Water / (Total Oil + Total Water)
        wcut = (wat / liquid * 100) if liquid > 0 else 0.0

        # Field GOR: Total Gas / Total Oil (Sm³/Sm³)
        gor = (gas / oil) if oil > 0 else 0.0

        active_days = (
            int((group["on_stream_hrs"] > 0).sum())
            if "on_stream_hrs" in group
            else len(group)
        )

        # Classification
        has_oil = oil > 0
        has_wi = wi > 0
        if has_oil and has_wi:
            role = "Producer & Injector"
        elif has_wi:
            role = "Injector"
        else:
            role = "Producer"

        records.append({
            "Well": well,
            "Role": role,
            "Cumulative Oil (Sm³)": oil,
            "Cumulative Gas (Sm³)": gas,
            "Cumulative Water (Sm³)": wat,
            "Cumulative Liquid (Sm³)": liquid,
            "Cumulative Water Injected (Sm³)": wi,
            "Water Cut (%)": wcut,
            "GOR (Sm³/Sm³)": gor,
            "Active Producing Days": active_days,
        })

    rankings_df = pd.DataFrame(records)
    if not rankings_df.empty:
        rankings_df = rankings_df.sort_values(
            by="Cumulative Oil (Sm³)", ascending=False
        ).reset_index(drop=True)
    return rankings_df


def get_producer_wells() -> list:
    """Return a sorted list of producer well names."""
    df = load_daily_production()
    producers = (
        df[df["well_type"] == "PRODUCER"]["well_bore_code"].dropna().unique()
    )
    return sorted(producers)
