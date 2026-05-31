import argparse
import os
import sys
from typing import List

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.azure_sql_connect import AzureSqlOperations


REQUIRED_ENV_VARS = [
    "TWELVE_DATA_API_KEY",
    "AZURE_SQL_SERVER",
    "AZURE_SQL_DATABASE",
    "AZURE_SQL_USERNAME",
    "AZURE_SQL_PASSWORD",
]


def parse_symbols(raw_symbols: str) -> List[str]:
    return [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate environment and Azure SQL connectivity")
    parser.add_argument("--symbols", default=os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    parser.add_argument("--table", default=os.getenv("AZURE_SQL_TABLE", "dbo.daily_stock_prices"))
    args = parser.parse_args()

    load_dotenv()

    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    symbols = parse_symbols(args.symbols)
    if not symbols:
        print("No symbols provided. Set SYMBOLS or pass --symbols.", file=sys.stderr)
        sys.exit(1)

    try:
        azure_sql = AzureSqlOperations()
        azure_sql.ensure_market_table(table_name=args.table)
        for symbol in symbols:
            _ = azure_sql.get_latest_datetime(table_name=args.table, symbol=symbol)
    except Exception as exc:
        print(f"Azure SQL preflight failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Preflight checks passed")


if __name__ == "__main__":
    main()
