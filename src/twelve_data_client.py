import time
from datetime import date
from typing import Dict, List, Optional

import pandas as pd
import requests

BASE_URL = "https://api.twelvedata.com/time_series"


class TwelveDataClient:
    """Simple Twelve Data API client tuned for daily OHLCV ingestion."""

    def __init__(self, api_key: str, interval: str = "1day", min_delay_seconds: int = 9) -> None:
        if not api_key:
            raise ValueError("TWELVE_DATA_API_KEY is required")
        self.api_key = api_key
        self.interval = interval
        self.min_delay_seconds = min_delay_seconds

    def fetch_daily_series(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        outputsize: int = 5000,
    ) -> pd.DataFrame:
        params: Dict[str, str | int] = {
            "symbol": symbol,
            "interval": self.interval,
            "apikey": self.api_key,
            "format": "JSON",
            "outputsize": outputsize,
            "order": "ASC",
        }

        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        if "status" in payload and payload["status"] == "error":
            raise RuntimeError(f"TwelveData error for {symbol}: {payload.get('message', 'unknown error')}")

        values: List[Dict[str, str]] = payload.get("values", [])
        if not values:
            return pd.DataFrame(columns=["datetime", "symbol", "open", "high", "low", "close", "volume"])

        frame = pd.DataFrame(values)
        frame["symbol"] = symbol

        expected = ["datetime", "symbol", "open", "high", "low", "close", "volume"]
        frame = frame[expected]

        # Normalize types for DB insert and local CSV conversion.
        frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.strftime("%Y-%m-%d")
        for col in ["open", "high", "low", "close", "volume"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

        frame = frame.dropna(subset=["datetime", "open", "high", "low", "close"]).drop_duplicates(
            subset=["symbol", "datetime"],
            keep="last",
        )

        return frame

    def respecting_rate_limit_sleep(self) -> None:
        time.sleep(self.min_delay_seconds)


DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")
