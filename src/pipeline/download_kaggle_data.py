"""
Download Volve production data from Kaggle.

Authentication (pick ONE approach, in priority order):
  1. kaggle.json   – place at ~/.kaggle/kaggle.json  (recommended)
  2. Environment   – set KAGGLE_USERNAME and KAGGLE_KEY in your shell
                     or in a .env file (never commit .env to git)

Run:
    python src/pipeline/download_kaggle_data.py
    python src/pipeline/download_kaggle_data.py --dest data/raw
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DEST = BASE_DIR / "data" / "raw"

DATASET_SLUG = "lamyalbert/volve-production-data"
EXPECTED_FILE = "Volve production data.xlsx"


def _load_dotenv() -> None:
    """Optionally load a .env file from the project root (python-dotenv)."""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv(env_path)
        except ImportError:
            # python-dotenv not installed – silently skip
            pass


def download(dest: Path) -> None:
    """Authenticate with Kaggle and download the dataset to *dest*."""
    dest.mkdir(parents=True, exist_ok=True)

    # Load .env if present (adds KAGGLE_USERNAME / KAGGLE_KEY to env)
    _load_dotenv()

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi  # type: ignore
    except ImportError:
        print("[ERROR] kaggle package not found. Install it with: pip install kaggle")
        sys.exit(1)

    api = KaggleApi()

    try:
        api.authenticate()
    except Exception as exc:
        print(
            "[ERROR] Kaggle authentication failed.\n"
            "  Make sure one of the following is configured:\n"
            "    • ~/.kaggle/kaggle.json  (recommended)\n"
            "    • KAGGLE_USERNAME and KAGGLE_KEY environment variables\n"
            "    • A .env file in the project root with those variables\n"
            f"  Details: {exc}"
        )
        sys.exit(1)

    print(f"Downloading dataset '{DATASET_SLUG}' → {dest} …")
    try:
        api.dataset_download_files(DATASET_SLUG, path=str(dest), unzip=True)
    except Exception as exc:
        print(f"[ERROR] Download failed: {exc}")
        print(
            f"  Check that you have accepted the dataset terms at:\n"
            f"  https://www.kaggle.com/datasets/{DATASET_SLUG}"
        )
        sys.exit(1)

    excel_file = dest / EXPECTED_FILE
    if excel_file.exists():
        print(f"[OK] File saved to: {excel_file}")
        print("\nExtracted files:")
        for item in sorted(dest.glob("*")):
            print(f"  - {item.name}")
    else:
        print("[WARNING] Download completed but expected file not found:")
        print(f"  Expected: {excel_file}")
        print("  Found:")
        for item in sorted(dest.glob("*")):
            print(f"    - {item.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Volve production data from Kaggle.")
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help=f"Destination directory (default: {DEFAULT_DEST})",
    )
    args = parser.parse_args()
    download(args.dest)


if __name__ == "__main__":
    main()