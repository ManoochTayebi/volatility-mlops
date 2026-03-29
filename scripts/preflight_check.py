import argparse
import os
import sys
from typing import List

from dotenv import load_dotenv

from src.supabase_connect import SupabaseOperations


REQUIRED_ENV_VARS = [
    "TWELVE_DATA_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
]


def parse_symbols(raw_symbols: str) -> List[str]:
    return [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate environment and Supabase connectivity")
    parser.add_argument("--symbols", default=os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    parser.add_argument("--table", default=os.getenv("SUPABASE_TABLE", "daily_stock_prices"))
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
        supabase = SupabaseOperations()
        for symbol in symbols:
            _ = supabase.get_latest_datetime(table_name=args.table, symbol=symbol)
    except Exception as exc:
        print(f"Supabase preflight failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Preflight checks passed")


if __name__ == "__main__":
    main()
