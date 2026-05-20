"""Load the three brand CSVs into a single DuckDB database and run SQL transforms.

Idempotent. Run from the project root:
    python src/data_loader.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

# Make `src` importable when run as a script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.festival_calendar import build_calendar  # noqa: E402

# CSVs live in the parent "marketing project/" directory, alongside this folder
RAW_DATA_DIR = ROOT.parent
DB_PATH = ROOT / "data" / "beauty.duckdb"
SQL_DIR = ROOT / "sql"

BRAND_FILES: dict[str, str] = {
    "purplle": "purplle_campaign_data.csv",
    "nykaa": "nykaa_campaign_data.csv",
    "tira": "tira_campaign_data.csv",
}


def load_brand_csvs() -> pd.DataFrame:
    """Read all brand CSVs, tag with brand, parse dates, concatenate."""
    frames = []
    for brand, fname in BRAND_FILES.items():
        path = RAW_DATA_DIR / fname
        if not path.exists():
            raise FileNotFoundError(f"Expected CSV not found: {path}")
        df = pd.read_csv(path)
        df["brand"] = brand
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
        frames.append(df)
        print(f"  loaded {brand:<8s} {len(df):>6,} rows from {fname}")
    return pd.concat(frames, ignore_index=True)


def run() -> None:
    print("=" * 60)
    print("Beauty Campaign Analytics — DuckDB loader")
    print("=" * 60)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nDB path: {DB_PATH}")

    con = duckdb.connect(str(DB_PATH))

    # 1. Raw campaigns
    print("\n[1/4] Loading raw CSVs into campaigns_raw …")
    raw = load_brand_csvs()
    con.register("raw_view", raw)
    con.execute("CREATE OR REPLACE TABLE campaigns_raw AS SELECT * FROM raw_view")
    n_raw = con.execute("SELECT COUNT(*) FROM campaigns_raw").fetchone()[0]
    print(f"      -> campaigns_raw: {n_raw:,} rows")

    # 2. Festival calendar
    print("\n[2/4] Building dim_calendar …")
    cal = build_calendar()
    con.register("cal_view", cal)
    con.execute("CREATE OR REPLACE TABLE dim_calendar AS SELECT * FROM cal_view")
    n_cal = con.execute("SELECT COUNT(*) FROM dim_calendar").fetchone()[0]
    print(f"      -> dim_calendar: {n_cal} days")

    # 3. SQL transforms (in numeric file order)
    print("\n[3/4] Running SQL transforms …")
    sql_files = sorted(SQL_DIR.glob("*.sql"))
    for f in sql_files:
        print(f"      -> {f.name}")
        con.execute(f.read_text())

    # 4. Sanity checks
    print("\n[4/4] Sanity checks …")
    objects = con.execute(
        "SELECT table_name, table_type FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()
    for name, kind in objects:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"      {kind:<10s} {name:<25s} {n:>8,} rows")
        except Exception as e:  # noqa: BLE001
            print(f"      {kind:<10s} {name:<25s} ERROR: {e}")

    con.close()
    print("\nDone.\n")


if __name__ == "__main__":
    run()
