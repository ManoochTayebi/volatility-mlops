import argparse
import os
import sys
from typing import List

import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.supabase_connect import SupabaseOperations


def parse_symbols(raw_symbols: str) -> List[str]:
    return [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]


def normalize_for_market_csv(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    frame = pd.DataFrame(rows)
    frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.strftime("%Y-%m-%d")

    for col in ["open", "high", "low", "close", "volume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame = frame.sort_values("datetime").drop_duplicates(subset=["datetime"], keep="last")

    renamed = frame.rename(
        columns={
            "datetime": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )

    return renamed[["Date", "Open", "High", "Low", "Close", "Volume"]]


def run(symbols: List[str], table_name: str, output_dir: str) -> None:
    load_dotenv()
    os.makedirs(output_dir, exist_ok=True)

    supabase = SupabaseOperations()

    for symbol in symbols:
        rows = supabase.fetch_symbol_rows(table_name=table_name, symbol=symbol)
        frame = normalize_for_market_csv(rows)
        output_path = os.path.join(output_dir, f"market_{symbol.lower()}.csv")
        frame.to_csv(output_path, index=False)
        print(f"[{symbol}] wrote {len(frame)} rows to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync market data from Supabase to local backend/data CSV files")
    parser.add_argument("--symbols", default=os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    parser.add_argument("--table", default=os.getenv("SUPABASE_TABLE", "daily_stock_prices"))
    parser.add_argument("--output-dir", default="backend/data")

    args = parser.parse_args()
    run(
        symbols=parse_symbols(args.symbols),
        table_name=args.table,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
