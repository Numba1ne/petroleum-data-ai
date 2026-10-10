import os
import zipfile
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

# Define paths
base_dir = Path(__file__).resolve().parents[2]
raw_dir = base_dir / 'data' / 'raw'
raw_dir.mkdir(parents=True, exist_ok=True)

# 1. Set environment variables for authentication - this is required
os.environ['KAGGLE_USERNAME'] = 'emmanuelanthony100'
os.environ['KAGGLE_KEY'] = 'KGAT_80731b199b31eab5e46a440ecd7670a6'

api = KaggleApi()
api.authenticate()  # Use the environment variables we just set

try:
    # Download dataset
    print("Downloading Volve production data...")
    api.dataset_download_files(
        'lamyalbert/volve-production-data', 
        path=str(raw_dir),
        unzip=True
    )
    
    # Verify download
    excel_file = raw_dir / "Volve production data.xlsx"
    if excel_file.exists():
        print(f"\nSuccess! File saved to: {excel_file}")
        
        # Additional files from zip
        print("\nFiles extracted:")
        items = list(raw_dir.glob('*'))
        for item in items:
            print(f"- {item.name}")
        print("\nDownload complete.")
    else:
        print("\nError: File not found after download. Please check Kaggle dataset.")
        print(f"Contents of {raw_dir}:")
        items = list(raw_dir.glob('*'))
        if items:
            for item in items:
                print(f"- {item.name}")
        else:
            print("Directory is empty")

except Exception as e:
    print(f"\nAn error occurred: {str(e)}")
    print("\nPlease verify:")
    print("1. Your Kaggle username and key are correct (set in code)")
    print(f"2. You've accepted Kaggle's dataset terms: https://www.kaggle.com/datasets/lamyalbert/volve-production-data")

# Securely clear credentials from memory
os.environ.pop('KAGGLE_USERNAME', None)
os.environ.pop('KAGGLE_KEY', None)
del api
print("Credentials securely cleared.")