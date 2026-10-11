"""
Verify that the Volve data pipeline produced the expected outputs.

Run from the repo root:
    python verify_data.py
"""

import sys
from pathlib import Path

# Allow importing src.config regardless of working directory
_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from config import (  # noqa: E402
    DAILY_CSV,
    DAILY_PARQUET,
    DB_PATH,
    MONTHLY_CSV,
    MONTHLY_PARQUET,
    QUALITY_REPORT_PATH,
    RAW_EXCEL_PATH,
)

CHECKS = [
    ("Raw Excel",              RAW_EXCEL_PATH),
    ("Daily CSV",              DAILY_CSV),
    ("Daily Parquet",          DAILY_PARQUET),
    ("Monthly CSV",            MONTHLY_CSV),
    ("Monthly Parquet",        MONTHLY_PARQUET),
    ("SQLite database",        DB_PATH),
    ("Data quality report",    QUALITY_REPORT_PATH),
]

passed = 0
failed = 0

print("\n================== Volve Pipeline Verification ==================")
for label, path in CHECKS:
    if path.exists():
        size_kb = path.stat().st_size / 1024
        print(f"  [OK]  {label:<25}  {path.name}  ({size_kb:,.0f} KB)")
        passed += 1
    else:
        print(f"  [!!]  {label:<25}  NOT FOUND: {path}")
        failed += 1

# Quick row count from SQLite if available
if DB_PATH.exists():
    try:
        import sqlite3
        con = sqlite3.connect(DB_PATH)
        daily_rows   = con.execute("SELECT COUNT(*) FROM daily_production").fetchone()[0]
        monthly_rows = con.execute("SELECT COUNT(*) FROM monthly_production").fetchone()[0]
        con.close()
        print(f"\n  Daily production rows:   {daily_rows:,}")
        print(f"  Monthly production rows: {monthly_rows:,}")
    except Exception as exc:
        print(f"\n  [WARNING] Could not query DB: {exc}")

print(f"\n  Result: {passed} passed, {failed} failed")
print("=================================================================\n")

if failed:
    sys.exit(1)