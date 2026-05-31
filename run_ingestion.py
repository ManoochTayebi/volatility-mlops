#!/usr/bin/env python3
"""Container-friendly entrypoint for full market-history ingestion."""

import os
import sys

from dotenv import load_dotenv

from scripts.ingest_market_data import parse_symbols, run
from src.twelve_data_client import DEFAULT_END_DATE


if __name__ == "__main__":
    load_dotenv()

    symbols = parse_symbols(os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    table = os.getenv("AZURE_SQL_TABLE", "dbo.daily_stock_prices")
    start_date = os.getenv("START_DATE", "2015-01-01")
    end_date = os.getenv("END_DATE", DEFAULT_END_DATE)

    print("Starting full ingestion for:", ", ".join(symbols))

    try:
        run(
            mode="full",
            symbols=symbols,
            table_name=table,
            start_date=start_date,
            end_date=end_date,
        )
        print("Ingestion completed successfully")
        sys.exit(0)
    except Exception as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        raise
