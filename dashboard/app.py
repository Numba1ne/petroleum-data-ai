import sys
from pathlib import Path

# Ensure project root is on the path. Imports below intentionally come after
# this bootstrap, hence `# noqa: E402` (Ruff "import not at top of file").
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard.utils import compute_well_rankings, get_producer_wells, load_daily_production  # noqa: E402
from forecasting.evaluate import evaluate_forecast  # noqa: E402
from forecasting.forecast import forecast_well  # noqa: E402

# -------------------------------------------------
# Page config (must be first Streamlit command)
# -------------------------------------------------
st.set_page_config(
    page_title="Volve Production Dashboard",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------
# Custom Styling
# -------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.5rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.6rem;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Data Loading
# -------------------------------------------------
try:
    df_raw = load_daily_production()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# -------------------------------------------------
# Sidebar: Controls & Filters
# -------------------------------------------------
st.sidebar.title("🛢️ Volve Controls")
st.sidebar.markdown("Filter production data by well role, wellbore, and dates.")

# Filter 1: Producer / Injector Filter
well_role_options = ["All Wells", "Producers Only", "Injectors Only"]
selected_role = st.sidebar.radio(
    "Well Role Filter",
    options=well_role_options,
    index=0,
    help="Filter wells by their operating function.",
)

# Apply role filtering to base dataframe
if selected_role == "Producers Only":
    df_role = df_raw[df_raw["well_type"] == "PRODUCER"].copy()
elif selected_role == "Injectors Only":
    df_role = df_raw[df_raw["well_type"] == "INJECTOR"].copy()
else:
    df_role = df_raw.copy()

# Filter 2: Well Selector
available_wells = sorted(df_role["well_bore_code"].dropna().unique())

# Smart defaults based on role
if selected_role == "Injectors Only":
    default_wells = available_wells
elif len(available_wells) >= 2:
    preferred_defaults = ["NO 15/9-F-12 H", "NO 15/9-F-14 H"]
    default_wells = [w for w in preferred_defaults if w in available_wells]
    if not default_wells:
        default_wells = available_wells[:2]
else:
    default_wells = available_wells

selected_wells = st.sidebar.multiselect(
    "Select Well(s)",
    options=available_wells,
    default=default_wells,
    help="Select one or more wellbores to visualize.",
)

# Filter 3: Date Range
min_date = df_raw["dateprd"].min().date()
max_date = df_raw["dateprd"].max().date()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# Filter data by well selection and dates
if not selected_wells:
    st.warning("⚠️ Please select at least one well from the sidebar to display data.")
    st.stop()

mask = (
    df_role["well_bore_code"].isin(selected_wells)
    & (df_role["dateprd"].dt.date >= start_date)
    & (df_role["dateprd"].dt.date <= end_date)
)
filtered_df = df_role[mask].copy()

if filtered_df.empty:
    st.info("No data available for the selected filters.")
    st.stop()

# -------------------------------------------------
# Header
# -------------------------------------------------
st.title("🛢️ Volve Field Production Dashboard")
st.caption(
    f"Analyzing **{len(selected_wells)}** selected well(s) ({selected_role}) from "
    f"**{start_date.strftime('%d %b %Y')}** to **{end_date.strftime('%d %b %Y')}**."
)

# -------------------------------------------------
# Better KPIs
# -------------------------------------------------
st.subheader("Field Performance Overview")

total_oil = filtered_df["bore_oil_vol"].sum()
total_gas = filtered_df["bore_gas_vol"].sum()
total_water = filtered_df["bore_wat_vol"].sum()
total_wi = filtered_df["bore_wi_vol"].sum() if "bore_wi_vol" in filtered_df.columns else 0.0

total_liquid = total_oil + total_water
overall_water_cut = (total_water / total_liquid * 100) if total_liquid > 0 else 0.0
overall_gor = (total_gas / total_oil) if total_oil > 0 else 0.0

producers_count = filtered_df[filtered_df["well_type"] == "PRODUCER"]["well_bore_code"].nunique()
injectors_count = filtered_df[filtered_df["well_type"] == "INJECTOR"]["well_bore_code"].nunique()

# KPI Row 1: Cumulative Volumes
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
kpi_col1.metric("Cumulative Oil", f"{total_oil:,.0f} Sm³", help="Total stock tank oil produced")
kpi_col2.metric("Cumulative Gas", f"{total_gas:,.0f} Sm³", help="Total gas volume produced")
kpi_col3.metric("Cumulative Water", f"{total_water:,.0f} Sm³", help="Total produced formation water")
kpi_col4.metric("Water Injected", f"{total_wi:,.0f} Sm³", help="Total water injected for pressure support")

# KPI Row 2: Diagnostic & Operational Metrics
kpi_col5, kpi_col6, kpi_col7, kpi_col8 = st.columns(4)
kpi_col5.metric(
    "Field Water Cut",
    f"{overall_water_cut:.1f}%",
    help="Cumulative Water / (Cumulative Oil + Water)",
)
kpi_col6.metric(
    "Average GOR",
    f"{overall_gor:,.1f} Sm³/Sm³",
    help="Cumulative Gas / Cumulative Oil",
)
kpi_col7.metric("Active Producers", f"{producers_count}", help="Distinct producing wells in selection")
kpi_col8.metric("Active Injectors", f"{injectors_count}", help="Distinct injection wells in selection")

st.divider()

# -------------------------------------------------
# Visualization Tabs
# -------------------------------------------------
tab_prod, tab_diag, tab_rank, tab_forecast = st.tabs([
    "📈 Production & Injection",
    "🧪 Diagnostics (Water Cut & GOR)",
    "🏆 Well Rankings & Breakdown",
    "🔮 Decline Curve & Forecast",
])

# -------------------------------------------------
# Tab 1: Production & Injection Over Time
# -------------------------------------------------
with tab_prod:
    st.markdown("### Daily Fluid Rates")

    # Chart 1: Daily Oil Production
    oil_df = filtered_df[filtered_df["bore_oil_vol"] > 0]
    if not oil_df.empty:
        fig_oil = px.line(
            oil_df,
            x="dateprd",
            y="bore_oil_vol",
            color="well_bore_code",
            title="Daily Oil Production Rate (Sm³/day)",
            labels={
                "dateprd": "Date",
                "bore_oil_vol": "Daily Oil (Sm³/day)",
                "well_bore_code": "Well",
            },
            template="plotly_white",
        )
        fig_oil.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig_oil, width="stretch")
    else:
        st.info("No oil production records for the selected well(s).")

    # Chart 2: Side-by-side Gas & Water Production
    col_gas, col_wat = st.columns(2)

    with col_gas:
        gas_df = filtered_df[filtered_df["bore_gas_vol"] > 0]
        if not gas_df.empty:
            fig_gas = px.line(
                gas_df,
                x="dateprd",
                y="bore_gas_vol",
                color="well_bore_code",
                title="Daily Gas Production Rate (Sm³/day)",
                labels={
                    "dateprd": "Date",
                    "bore_gas_vol": "Gas Rate (Sm³/day)",
                    "well_bore_code": "Well",
                },
                template="plotly_white",
            )
            fig_gas.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_gas, width="stretch")
        else:
            st.info("No gas production for selected wells.")

    with col_wat:
        wat_df = filtered_df[filtered_df["bore_wat_vol"] > 0]
        if not wat_df.empty:
            fig_wat = px.line(
                wat_df,
                x="dateprd",
                y="bore_wat_vol",
                color="well_bore_code",
                title="Daily Produced Water Rate (Sm³/day)",
                labels={
                    "dateprd": "Date",
                    "bore_wat_vol": "Water Rate (Sm³/day)",
                    "well_bore_code": "Well",
                },
                template="plotly_white",
            )
            fig_wat.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_wat, width="stretch")
        else:
            st.info("No produced water for selected wells.")

    # Chart 3: Water Injection Rate (if injection wells present)
    inj_df = filtered_df[filtered_df["bore_wi_vol"] > 0]
    if not inj_df.empty:
        st.markdown("### Water Injection Rate")
        fig_wi = px.line(
            inj_df,
            x="dateprd",
            y="bore_wi_vol",
            color="well_bore_code",
            title="Daily Water Injection Rate (Sm³/day)",
            labels={
                "dateprd": "Date",
                "bore_wi_vol": "Injection Rate (Sm³/day)",
                "well_bore_code": "Well",
            },
            template="plotly_white",
        )
        fig_wi.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_wi, width="stretch")


# -------------------------------------------------
# Tab 2: Reservoir Diagnostics (Water Cut & GOR)
# -------------------------------------------------
with tab_diag:
    st.markdown("### Reservoir Performance & Breakthrough Diagnostics")

    # Prepare diagnostic dataframe
    diag_df = filtered_df.dropna(subset=["water_cut", "gor"]).copy()
    diag_df = diag_df[diag_df["water_cut"] >= 0]
    diag_df["water_cut_pct"] = diag_df["water_cut"] * 100

    if not diag_df.empty:
        col_wc, col_gor = st.columns(2)

        with col_wc:
            fig_wc = px.line(
                diag_df,
                x="dateprd",
                y="water_cut_pct",
                color="well_bore_code",
                title="Water Cut History (%)",
                labels={
                    "dateprd": "Date",
                    "water_cut_pct": "Water Cut (%)",
                    "well_bore_code": "Well",
                },
                template="plotly_white",
            )
            fig_wc.add_hline(
                y=50,
                line_dash="dot",
                line_color="orange",
                annotation_text="50% Water Cut",
                annotation_position="bottom right",
            )
            fig_wc.add_hline(
                y=80,
                line_dash="dash",
                line_color="red",
                annotation_text="80% High Water Cut",
                annotation_position="top right",
            )
            fig_wc.update_yaxes(range=[0, 105])
            fig_wc.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_wc, width="stretch")

        with col_gor:
            gor_plot_df = diag_df[diag_df["gor"] <= 500].copy()
            fig_gor = px.line(
                gor_plot_df,
                x="dateprd",
                y="gor",
                color="well_bore_code",
                title="Gas-Oil Ratio (GOR) History (Sm³/Sm³)",
                labels={
                    "dateprd": "Date",
                    "gor": "GOR (Sm³/Sm³)",
                    "well_bore_code": "Well",
                },
                template="plotly_white",
            )
            fig_gor.add_hline(
                y=150,
                line_dash="dot",
                line_color="green",
                annotation_text="Field Baseline (~150 Sm³/Sm³)",
                annotation_position="bottom right",
            )
            fig_gor.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20),
            )
            st.plotly_chart(fig_gor, width="stretch")
    else:
        st.info("No Water Cut or GOR diagnostic data available for selected well(s).")


# -------------------------------------------------
# Tab 3: Well Rankings & Cumulative Production
# -------------------------------------------------
with tab_rank:
    st.markdown("### Cumulative Performance Ranking")

    # Compute rankings on filtered dataset
    rankings_df = compute_well_rankings(filtered_df)

    if not rankings_df.empty:
        # Visual breakdown: Cumulative Oil & Water
        fig_bar = px.bar(
            rankings_df,
            x="Well",
            y=["Cumulative Oil (Sm³)", "Cumulative Water (Sm³)"],
            barmode="group",
            title="Cumulative Fluid Production by Well (Sm³)",
            labels={"value": "Volume (Sm³)", "variable": "Fluid Type"},
            color_discrete_map={
                "Cumulative Oil (Sm³)": "#2E7D32",
                "Cumulative Water (Sm³)": "#1565C0",
            },
            template="plotly_white",
        )
        fig_bar.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_bar, width="stretch")

        st.markdown("#### Detailed Well Leaderboard")
        st.dataframe(
            rankings_df,
            column_config={
                "Well": st.column_config.TextColumn("Wellbore", width="medium"),
                "Role": st.column_config.TextColumn("Role", width="small"),
                "Cumulative Oil (Sm³)": st.column_config.NumberColumn(
                    "Cum Oil (Sm³)", format="%,.0f"
                ),
                "Cumulative Gas (Sm³)": st.column_config.NumberColumn(
                    "Cum Gas (Sm³)", format="%,.0f"
                ),
                "Cumulative Water (Sm³)": st.column_config.NumberColumn(
                    "Cum Water (Sm³)", format="%,.0f"
                ),
                "Cumulative Liquid (Sm³)": st.column_config.NumberColumn(
                    "Cum Liquid (Sm³)", format="%,.0f"
                ),
                "Cumulative Water Injected (Sm³)": st.column_config.NumberColumn(
                    "Cum Injected (Sm³)", format="%,.0f"
                ),
                "Water Cut (%)": st.column_config.ProgressColumn(
                    "Water Cut (%)",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "GOR (Sm³/Sm³)": st.column_config.NumberColumn(
                    "GOR (Sm³/Sm³)", format="%.1f"
                ),
                "Active Producing Days": st.column_config.NumberColumn(
                    "Active Days", format="%d"
                ),
            },
            hide_index=True,
            width="stretch",
        )

        # Download CSV
        csv_data = rankings_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Ranking Table as CSV",
            data=csv_data,
            file_name="volve_well_rankings.csv",
            mime="text/csv",
        )
    else:
        st.info("No well data to rank.")

# -------------------------------------------------
# Tab 4: Decline Curve & Forecast
# -------------------------------------------------
with tab_forecast:
    st.markdown("### Decline Curve Analysis & Production Forecast")
    st.caption("Arps Exponential / Hyperbolic models fitted on historical oil rates.")

    producer_wells = get_producer_wells()

    if not producer_wells:
        st.info("No producer wells available in the dataset.")
    else:
        # Controls
        col_f1, col_f2 = st.columns([2, 1])

        with col_f1:
            default_well = (
                "NO 15/9-F-12 H" if "NO 15/9-F-12 H" in producer_wells else producer_wells[0]
            )
            selected_forecast_well = st.selectbox(
                "Select Producer Well",
                options=producer_wells,
                index=producer_wells.index(default_well),
            )

        with col_f2:
            forecast_horizon = st.slider(
                "Forecast Horizon (days)",
                min_value=90,
                max_value=730,
                value=365,
                step=30,
            )

        if st.button("Run Forecast", type="primary"):
            with st.spinner(f"Fitting decline curve for {selected_forecast_well}..."):
                try:
                    result = forecast_well(
                        selected_forecast_well,
                        forecast_days=forecast_horizon,
                        train_frac=0.8,
                    )
                    metrics = evaluate_forecast(result)

                    if "error" in result:
                        st.error(result["error"])
                    else:
                        # --- Parameter cards ---
                        st.subheader("Model Parameters")
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Model", result["model"].title())
                        m2.metric("Initial Rate qi", f"{result['qi']:,.0f} Sm³/d")
                        m3.metric("Decline di", f"{result['di']:.6f} /day")
                        m4.metric("Train R²", f"{result['r2_train']:.3f}")

                        if result["b"] is not None:
                            st.caption(f"Hyperbolic exponent b = {result['b']:.3f}")

                        # --- Evaluation metrics ---
                        st.subheader("Test Set Performance")
                        e1, e2, e3 = st.columns(3)
                        e1.metric("MAPE (Test)", f"{metrics.get('mape_test', float('nan')):.1f} %")
                        e2.metric("RMSE (Test)", f"{metrics.get('rmse_test', float('nan')):,.1f} Sm³/d")
                        e3.metric("Test Points", metrics.get("n_test", 0))

                        # --- Interactive Plotly chart ---
                        st.subheader("Actual vs Model Fit + Forecast")
                        fdf = result["forecast_df"]

                        fig = go.Figure()

                        hist = fdf[fdf["segment"] == "history"]
                        fig.add_trace(go.Scatter(
                            x=hist["date"],
                            y=hist["actual_oil"],
                            mode="markers",
                            name="Actual",
                            marker=dict(size=5, opacity=0.5, color="steelblue"),
                        ))

                        fig.add_trace(go.Scatter(
                            x=hist["date"],
                            y=hist["predicted_oil"],
                            mode="lines",
                            name=f"Fit ({result['model']})",
                            line=dict(color="darkorange", width=2),
                        ))

                        fut = fdf[fdf["segment"] == "forecast"]
                        fig.add_trace(go.Scatter(
                            x=fut["date"],
                            y=fut["predicted_oil"],
                            mode="lines",
                            name="Forecast",
                            line=dict(color="crimson", width=2, dash="dash"),
                        ))

                        fig.update_layout(
                            title=f"{selected_forecast_well} – Decline Curve Forecast",
                            xaxis_title="Date",
                            yaxis_title="Oil Rate (Sm³/day)",
                            hovermode="x unified",
                            template="plotly_white",
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1,
                            ),
                            height=500,
                        )
                        st.plotly_chart(fig, width="stretch")

                        # Download button for this forecast
                        forecast_csv = fdf.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Download this forecast (CSV)",
                            data=forecast_csv,
                            file_name=(
                                f"{selected_forecast_well.replace('/', '').replace(' ', '')}_forecast.csv"
                            ),
                            mime="text/csv",
                        )

                except Exception as e:
                    st.error(f"Forecast failed: {e}")


# -------------------------------------------------
# Export Filtered Data
# -------------------------------------------------
st.divider()
st.subheader("Export")

csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered data as CSV",
    data=csv,
    file_name="volve_filtered_production.csv",
    mime="text/csv",
    help="Downloads the currently filtered daily production data",
)