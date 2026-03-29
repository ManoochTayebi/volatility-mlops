import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseOperations:
    """Thin wrapper around Supabase for market data ingestion and export."""

    def __init__(self) -> None:
        load_dotenv()
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        self.supabase: Client = create_client(url, key)

    def get_latest_datetime(self, table_name: str, symbol: str) -> Optional[str]:
        response = (
            self.supabase.table(table_name)
            .select("datetime")
            .eq("symbol", symbol)
            .order("datetime", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]["datetime"]

    def upsert_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        # Requires a unique constraint on (symbol, datetime).
        try:
            self.supabase.table(table_name).upsert(rows, on_conflict="symbol,datetime").execute()
        except Exception as exc:
            # Some existing tables have an update trigger that references columns
            # not present in the table. In that case, gracefully fall back to
            # "insert if missing" so ingestion can still proceed.
            if "updated_at" not in str(exc):
                raise
            print(
                "Upsert update path failed because of an 'updated_at' trigger mismatch. "
                "Falling back to conflict-ignore insert mode."
            )
            self.supabase.table(table_name).upsert(
                rows,
                on_conflict="symbol,datetime",
                ignore_duplicates=True,
            ).execute()
        return len(rows)

    def fetch_symbol_rows(self, table_name: str, symbol: str, page_size: int = 1000) -> List[Dict[str, Any]]:
        all_rows: List[Dict[str, Any]] = []
        offset = 0

        while True:
            response = (
                self.supabase.table(table_name)
                .select("datetime,symbol,open,high,low,close,volume")
                .eq("symbol", symbol)
                .order("datetime", desc=False)
                .range(offset, offset + page_size - 1)
                .execute()
            )

            page = response.data or []
            if not page:
                break

            all_rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size

        return all_rows


# Backward-compatible alias used in older files.
SupaBaseOperations = SupabaseOperations
