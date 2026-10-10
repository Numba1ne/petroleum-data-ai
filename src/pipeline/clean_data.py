import pandas as pd
import numpy as np
import os
import sys
from sqlalchemy import create_engine
from pathlib import Path

# Define paths
base_dir = Path(__file__).resolve().parents[2]
raw_data_path = base_dir / 'data' / 'raw' / 'Volve production data.xlsx'
processed_dir = base_dir / 'data' / 'processed'
db_dir = base_dir / 'data' / 'db'
report_dir = base_dir / 'reports'

# Create directories if needed
processed_dir.mkdir(parents=True, exist_ok=True)
db_dir.mkdir(parents=True, exist_ok=True)
report_dir.mkdir(parents=True, exist_ok=True)

# Data quality report container
data_quality_notes = []

def load_and_clean_data():
    """Load and clean Volve production data"""
    try:
        # Load data
        daily = pd.read_excel(raw_data_path, sheet_name="Daily Production Data")
        monthly = pd.read_excel(raw_data_path, sheet_name="Monthly Production Data")
        
        # Initial data quality checks
        data_quality_notes.append(f"Raw daily data shape: {daily.shape}")
        data_quality_notes.append(f"Date range: {daily['DATEPRD'].min()} to {daily['DATEPRD'].max()}")
        data_quality_notes.append(f"Unique wells: {len(daily['WELL_BORE_CODE'].unique())}")
        data_quality_notes.append(f"Raw monthly data shape: {monthly.shape}")
        
        # Copy data for cleaning
        daily_clean = daily.copy()
        monthly_clean = monthly.copy()
        
        # 1. Standardize column names
        daily_clean.columns = (daily_clean.columns
                              .str.lower()
                              .str.replace(' ', '_')
                              .str.replace(r'[()]', '', regex=True))        
        # 2. Parse DATEPRD to datetime
        daily_clean['dateprd'] = pd.to_datetime(daily_clean['dateprd'])
        
        # 3. Identify and flag producer vs injector wells
        flow_mapping = {}
        for well in daily_clean['well_bore_code'].unique():
            well_data = daily_clean[daily_clean['well_bore_code'] == well]
            # Check for presence of injection data
            has_injection = well_data['bore_wi_vol'].notna().any()
            flow_mapping[well] = 'INJECTOR' if has_injection else 'PRODUCER'
        
        daily_clean['well_type'] = daily_clean['well_bore_code'].map(flow_mapping)
        
        # 4. Calculate derived metrics
        # Water Cut = Water Volume / (Oil Volume + Water Volume)
        daily_clean['water_cut'] = daily_clean['bore_wat_vol'] / \
            (daily_clean['bore_oil_vol'] + daily_clean['bore_wat_vol'])
            
        # Gas-Oil Ratio = Gas Volume / Oil Volume
        daily_clean['gor'] = daily_clean['bore_gas_vol'] / daily_clean['bore_oil_vol']
        
        # Handle division by zero
        daily_clean.loc[daily_clean['bore_oil_vol'] == 0, 'gor'] = 0
            
        # Onstream efficiency
        daily_clean['onstream_efficiency'] = daily_clean['on_stream_hrs'] / 24
        
        # 5. Handle missing values
        # Report missing values before handling
        missing_before = daily_clean.isna().sum()
        
        # Fill pressure/temperature measurements with rolling averages
        for col in ['avg_downhole_pressure', 'avg_downhole_temperature', 'dp_choke_size']:
            daily_clean[col] = (daily_clean.groupby('well_bore_code')[col]
                                  .transform(lambda x: x.fillna(x.rolling(3, min_periods=1).mean())))
        
        # Report missing values after handling
        missing_after = daily_clean.isna().sum()
        
        # Add to data quality report
        data_quality_notes.append("\nMissing values before handling:")
        data_quality_notes.append(str(missing_before[missing_before > 0]))
        data_quality_notes.append("\nMissing values after handling:")
        data_quality_notes.append(str(missing_after[missing_after > 0]))
        
        # Report summary stats
        data_quality_notes.append("\nSummary statistics for cleaned daily data:")
        data_quality_notes.append(daily_clean.describe().to_string())
        
        return daily_clean
        
    except FileNotFoundError:
        print(f"Error: Raw data file not found at {raw_data_path}")
        print("Please download the Volve data and place in data/raw/")
        sys.exit(1)

def save_data(df, engine):
    """Save data to various formats"""
    # Save to CSV and Parquet
    df.to_csv(processed_dir / "daily_production_clean.csv", index=False)
    df.to_parquet(processed_dir / "daily_production_clean.parquet", index=False)
    
    # Save to SQL database
    df.to_sql("daily_production", engine, if_exists="replace", index=False)
    
    # Save data quality report
    with open(report_dir / "data_quality_report.md", "w") as f:
        f.write("# Volve Production Data Quality Report\n\n")
        f.write("## Key Findings\n\n")
        f.write("\n".join(data_quality_notes))

if __name__ == "__main__":
    # Create DB engine
    db_path = db_dir / "volve_production.db"
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Process data
    cleaned_daily = load_and_clean_data()
    
    # Save processed data
    save_data(cleaned_daily, engine)
    
    print("Data processing complete!")
    print(f"- Cleaned CSV saved to: {processed_dir / 'daily_production_clean.csv'}")
    print(f"- Database saved to: {db_path}")
    print(f"- Data quality report: {report_dir / 'data_quality_report.md'}")