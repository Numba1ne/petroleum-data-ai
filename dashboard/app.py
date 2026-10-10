import dash
from dash import html, dcc
import plotly.express as px
import pandas as pd
import sqlite3
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "db" / "volve_production.db"

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Volve Production Dashboard"

# Connect to database
def load_production_data():
    """Load daily production data from SQLite"""
    engine = sqlite3.connect(DB_PATH)
    query = "SELECT well_bore_code, dateprd, bore_oil_vol, bore_gas_vol, bore_wat_vol, water_cut, gor FROM daily_production ORDER BY dateprd"
    return pd.read_sql_query(query, engine)

# Create plotly figure
def create_production_plot(df):
    """Generate time series production plot"""
    fig = px.line(df, 
                 x="dateprd", 
                 y="bore_oil_vol", 
                 color="well_bore_code",
                 title="Daily Oil Production by Well",
                 labels={"bore_oil_vol": "Oil Volume (bbl)", "dateprd": "Date"})
    fig.update_layout(hovermode="x unified")
    return fig

# Load data
df = load_production_data()

# App layout
app.layout = html.Div([
    html.H1("Volve Field Production Dashboard"),
    
    dcc.Graph(
        id='production-plot',
        figure=create_production_plot(df)
    ),
    
    html.Div([
        html.Label("Select Metric:"),
        dcc.Dropdown(
            id='metric-selector',
            options=[
                {'label': 'Oil Volume', 'value': 'bore_oil_vol'},
                {'label': 'Gas Volume', 'value': 'bore_gas_vol'},
                {'label': 'Water Volume', 'value': 'bore_wat_vol'},
                {'label': 'Water Cut', 'value': 'water_cut'},
                {'label': 'Gas-Oil Ratio', 'value': 'gor'}
            ],
            value='bore_oil_vol'
        )
    ], style={'width': '30%', 'margin': '20px'})
])

if __name__ == '__main__':
    app.run_server(debug=True)