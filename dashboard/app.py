import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from sqlalchemy import create_engine

# -------------------------------------------------
# Page config (must be first Streamlit command)
# -------------------------------------------------
st.set_page_config(
    page_title="Volve Production Dashboard",
    page_icon="🛢️",
    layout="wide"
)

# -------------------------------------------------
# Paths
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"

# -------------------------------------------------
# Data loading (with caching)
# -------------------------------------------------
@st.cache_data
def load_data():
    if not DB_PATH.exists():
        st.error("Database not found. Please run Project 1 pipeline first.")
        st.stop()
    
    engine = create_engine(f"sqlite:///{DB_PATH}")
    df = pd.read_sql("SELECT * FROM daily_production", engine)
    df["dateprd"] = pd.to_datetime(df["dateprd"])
    return df

df = load_data()

# -------------------------------------------------
# Title
# -------------------------------------------------
st.title("🛢️ Volve Field Production Dashboard")
st.markdown("Interactive exploration of cleaned daily production data")

# -------------------------------------------------
# Basic KPIs
# -------------------------------------------------
st.subheader("Field Overview")

col1, col2, col3, col4 = st.columns(4)

total_oil = df["bore_oil_vol"].sum()
total_gas = df["bore_gas_vol"].sum()
total_water = df["bore_wat_vol"].sum()
n_wells = df["well_bore_code"].nunique()

col1.metric("Total Oil (Sm³)", f"{total_oil:,.0f}")
col2.metric("Total Gas (Sm³)", f"{total_gas:,.0f}")
col3.metric("Total Water (Sm³)", f"{total_water:,.0f}")
col4.metric("Number of Wells", n_wells)

st.divider()

# -------------------------------------------------
# First interactive element – Well selector
# -------------------------------------------------
st.subheader("Production Over Time")

wells = sorted(df["well_bore_code"].dropna().unique())
selected_wells = st.multiselect(
    "Select well(s)",
    options=wells,
    default=wells[:2] if len(wells) >= 2 else wells
)

if selected_wells:
    filtered = df[df["well_bore_code"].isin(selected_wells)]
    
    fig = px.line(
        filtered,
        x="dateprd",
        y="bore_oil_vol",
        color="well_bore_code",
        title="Daily Oil Production",
        labels={"dateprd": "Date", "bore_oil_vol": "Oil Volume (Sm³)", "well_bore_code": "Well"}
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Please select at least one well.")