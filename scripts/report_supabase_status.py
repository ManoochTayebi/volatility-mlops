import argparse
import os
import sys
from typing import List
from urllib.parse import urlparse

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.supabase_connect import SupabaseOperations


def parse_symbols(raw_symbols: str) -> List[str]:
    return [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]


def mask_host(url: str) -> str:
    host = urlparse(url).netloc or "unknown-host"
    if len(host) <= 12:
        return host
    return f"{host[:8]}...{host[-8:]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Report masked Supabase target and latest dates per symbol")
    parser.add_argument("--symbols", default=os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    parser.add_argument("--table", default=os.getenv("SUPABASE_TABLE", "daily_stock_prices"))
    args = parser.parse_args()

    load_dotenv()

    url = os.getenv("SUPABASE_URL", "")
    if not url:
        print("SUPABASE_URL is missing", file=sys.stderr)
        sys.exit(1)

    symbols = parse_symbols(args.symbols)
    supabase = SupabaseOperations()

    print(f"Supabase target host: {mask_host(url)}")
    print(f"Supabase table: {args.table}")

    for symbol in symbols:
        latest = supabase.get_latest_datetime(table_name=args.table, symbol=symbol)
        print(f"{symbol}: latest datetime = {latest or 'NONE'}")


if __name__ == "__main__":
    main()
