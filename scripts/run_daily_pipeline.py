import argparse
import os
import subprocess
from typing import List


def run_step(cmd: List[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run end-to-end daily MLOps pipeline")
    parser.add_argument("--symbols", default=os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    parser.add_argument("--table", default=os.getenv("SUPABASE_TABLE", "daily_stock_prices"))
    args = parser.parse_args()
    sync_market_csv = os.getenv("SYNC_MARKET_CSV", "false").lower() == "true"

    run_step([
        "python",
        "scripts/preflight_check.py",
        "--symbols",
        args.symbols,
        "--table",
        args.table,
    ])

    run_step([
        "python",
        "scripts/ingest_market_data.py",
        "--mode",
        "daily",
        "--symbols",
        args.symbols,
        "--table",
        args.table,
    ])

    if sync_market_csv:
        run_step([
            "python",
            "scripts/sync_market_data_from_supabase.py",
            "--symbols",
            args.symbols,
            "--table",
            args.table,
        ])
    else:
        print("Skipping market CSV sync because SYNC_MARKET_CSV is false")

    run_step([
        "python",
        "scripts/retrain_with_mlflow.py",
        "--symbols",
        args.symbols,
    ])


if __name__ == "__main__":
    main()
