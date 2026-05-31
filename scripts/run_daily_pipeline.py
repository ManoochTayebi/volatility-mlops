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
    parser.add_argument("--table", default=os.getenv("AZURE_SQL_TABLE", "dbo.daily_stock_prices"))
    args = parser.parse_args()
    os.environ["SYMBOLS"] = args.symbols
    os.environ["AZURE_SQL_TABLE"] = args.table

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

    run_step([
        "python",
        "scripts/retrain_with_mlflow.py",
        "--symbols",
        args.symbols,
    ])

    if os.getenv("AZURE_UPLOAD_ARTIFACTS", "false").lower() == "true":
        run_step([
            "python",
            "scripts/upload_artifacts_to_azure_blob.py",
        ])


if __name__ == "__main__":
    main()
