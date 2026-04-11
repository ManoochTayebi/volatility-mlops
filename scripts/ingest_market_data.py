import argparse
import os
import sys
from datetime import timedelta
from typing import List

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.supabase_connect import SupabaseOperations
from src.twelve_data_client import DEFAULT_END_DATE, DEFAULT_START_DATE, TwelveDataClient


def parse_symbols(raw_symbols: str) -> List[str]:
    return [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]


def build_start_date(mode: str, latest_datetime: str | None, default_start_date: str) -> str:
    if mode == "full" or not latest_datetime:
        return default_start_date

    latest = pd.to_datetime(latest_datetime)
    # Add a small overlap window to absorb delayed corrections from the API.
    return (latest - timedelta(days=3)).strftime("%Y-%m-%d")


def run(mode: str, symbols: List[str], table_name: str, start_date: str, end_date: str) -> None:
    load_dotenv()
    twelve_key = os.getenv("TWELVE_DATA_API_KEY")

    supabase = SupabaseOperations()
    client = TwelveDataClient(api_key=twelve_key)

    print(f"Starting ingestion in {mode} mode for {len(symbols)} symbols into {table_name}")

    for symbol in symbols:
        latest_dt = supabase.get_latest_datetime(table_name=table_name, symbol=symbol)
        symbol_start = build_start_date(mode=mode, latest_datetime=latest_dt, default_start_date=start_date)

        df = client.fetch_daily_series(
            symbol=symbol,
            start_date=symbol_start,
            end_date=end_date,
            outputsize=5000,
        )

        if df.empty:
            print(f"[{symbol}] no rows returned from API")
            client.respecting_rate_limit_sleep()
            continue

        inserted = supabase.upsert_rows(
            table_name=table_name,
            rows=df.to_dict(orient="records"),
        )
        print(f"[{symbol}] upserted {inserted} rows (from {symbol_start} to {end_date})")
        client.respecting_rate_limit_sleep()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Ingest market prices from Twelve Data into Supabase")
    parser.add_argument("--mode", choices=["daily", "full"], default=os.getenv("INGEST_MODE", "daily"))
    parser.add_argument("--symbols", default=os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    parser.add_argument("--table", default=os.getenv("SUPABASE_TABLE", "daily_stock_prices"))
    parser.add_argument("--start-date", default=os.getenv("START_DATE", DEFAULT_START_DATE))
    parser.add_argument("--end-date", default=os.getenv("END_DATE", DEFAULT_END_DATE))

    args = parser.parse_args()

    run(
        mode=args.mode,
        symbols=parse_symbols(args.symbols),
        table_name=args.table,
        start_date=args.start_date,
        end_date=args.end_date,
    )


if __name__ == "__main__":
    main()
