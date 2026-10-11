"""
One-time helper: write ~/.kaggle/kaggle.json from CLI arguments.

Usage:
    python setup_kaggle.py --username <your_username> --key <your_api_key>

Get your API key from: https://www.kaggle.com/settings → "Create New Token"
The generated kaggle.json will be written to ~/.kaggle/kaggle.json.

NOTE: Never put your real key in this script or commit it to git.
"""

import argparse
import json
import os
from pathlib import Path


def setup_kaggle_api(username: str, api_key: str) -> None:
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)

    config_path = kaggle_dir / "kaggle.json"
    config = {"username": username, "key": api_key}

    with open(config_path, "w") as f:
        json.dump(config, f)

    # Restrict permissions on POSIX systems (Linux/macOS)
    if os.name != "nt":
        os.chmod(config_path, 0o600)

    print(f"[OK] Kaggle credentials written to: {config_path}")
    print("     You can now run: python src/pipeline/download_kaggle_data.py")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write Kaggle API credentials to ~/.kaggle/kaggle.json"
    )
    parser.add_argument("--username", required=True, help="Your Kaggle username")
    parser.add_argument("--key", required=True, help="Your Kaggle API key")
    args = parser.parse_args()
    setup_kaggle_api(args.username, args.key)


if __name__ == "__main__":
    main()