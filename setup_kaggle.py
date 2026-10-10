import os
import json
from pathlib import Path

# Configuring Kaggle API
def setup_kaggle_api(username, api_key):
    # Create .kaggle directory
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    
    # Create kaggle.json
    config = {"username": username, "key": api_key}
    with open(kaggle_dir / "kaggle.json", "w") as f:
        json.dump(config, f)
    
    # Set secure permissions (required on Linux/Mac, recommended on Windows)
    if os.name != "nt":
        os.chmod(kaggle_dir / "kaggle.json", 0o600)
    
    print(f"Kaggle API configured for user: {username}")

if __name__ == "__main__":
    username = "emmanuelanthony100"
    api_key = "KGAT_80731b199b31eab5e46a440ecd7670a6"
    setup_kaggle_api(username, api_key)