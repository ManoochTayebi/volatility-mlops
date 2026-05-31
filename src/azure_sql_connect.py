import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


class AzureSqlOperations:
    """Azure SQL helper for market data ingestion and training reads."""

    def __init__(self) -> None:
        load_dotenv()
        self.server = os.getenv("AZURE_SQL_SERVER")
        self.database = os.getenv("AZURE_SQL_DATABASE")
        self.username = os.getenv("AZURE_SQL_USERNAME")
        self.password = os.getenv("AZURE_SQL_PASSWORD")
        if not all([self.server, self.database, self.username, self.password]):
            raise ValueError(
                "AZURE_SQL_SERVER, AZURE_SQL_DATABASE, AZURE_SQL_USERNAME, "
                "and AZURE_SQL_PASSWORD must be set"
            )

    def _connect(self):
        import pymssql

        server = self.server.replace("tcp:", "").split(",")[0]
        return pymssql.connect(
            server=server,
            user=self.username,
            password=self.password,
            database=self.database,
            login_timeout=30,
            timeout=60,
        )

    @staticmethod
    def _qualified_table(table_name: str) -> str:
        parts = table_name.split(".")
        if len(parts) == 1:
            parts = ["dbo", parts[0]]
        if len(parts) != 2:
            raise ValueError("Azure SQL table name must be table or schema.table")
        for part in parts:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
                raise ValueError(f"Unsafe Azure SQL identifier: {part}")
        return f"[{parts[0]}].[{parts[1]}]"

    def ensure_market_table(self, table_name: str) -> None:
        schema, table = table_name.split(".", 1) if "." in table_name else ("dbo", table_name)
        for identifier in (schema, table):
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
                raise ValueError(f"Unsafe Azure SQL identifier: {identifier}")

        qualified = self._qualified_table(table_name)
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    IF SCHEMA_ID(%s) IS NULL
                        EXEC('CREATE SCHEMA [{schema}]');

                    IF OBJECT_ID(%s, 'U') IS NULL
                    BEGIN
                        CREATE TABLE {qualified} (
                            [datetime] date NOT NULL,
                            [symbol] varchar(16) NOT NULL,
                            [open] float NOT NULL,
                            [high] float NOT NULL,
                            [low] float NOT NULL,
                            [close] float NOT NULL,
                            [volume] bigint NULL,
                            [created_at] datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
                            [updated_at] datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
                            CONSTRAINT [pk_{schema}_{table}_symbol_datetime]
                                PRIMARY KEY ([symbol], [datetime])
                        );
                    END
                    """,
                    (schema, f"{schema}.{table}"),
                )
            conn.commit()

    def get_latest_datetime(self, table_name: str, symbol: str) -> Optional[str]:
        qualified = self._qualified_table(table_name)
        with self._connect() as conn:
            with conn.cursor(as_dict=True) as cursor:
                cursor.execute(
                    f"""
                    SELECT TOP 1 CONVERT(varchar(10), [datetime], 23) AS [datetime]
                    FROM {qualified}
                    WHERE [symbol] = %s
                    ORDER BY [datetime] DESC
                    """,
                    (symbol,),
                )
                row = cursor.fetchone()
        return row["datetime"] if row else None

    def upsert_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0

        self.ensure_market_table(table_name)
        qualified = self._qualified_table(table_name)
        sql = f"""
            MERGE {qualified} WITH (HOLDLOCK) AS target
            USING (
                SELECT
                    CAST(%s AS date) AS [datetime],
                    CAST(%s AS varchar(16)) AS [symbol],
                    CAST(%s AS float) AS [open],
                    CAST(%s AS float) AS [high],
                    CAST(%s AS float) AS [low],
                    CAST(%s AS float) AS [close],
                    CAST(%s AS bigint) AS [volume]
            ) AS source
            ON target.[symbol] = source.[symbol]
               AND target.[datetime] = source.[datetime]
            WHEN MATCHED THEN
                UPDATE SET
                    [open] = source.[open],
                    [high] = source.[high],
                    [low] = source.[low],
                    [close] = source.[close],
                    [volume] = source.[volume],
                    [updated_at] = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT ([datetime], [symbol], [open], [high], [low], [close], [volume])
                VALUES (
                    source.[datetime], source.[symbol], source.[open],
                    source.[high], source.[low], source.[close], source.[volume]
                );
        """

        with self._connect() as conn:
            with conn.cursor() as cursor:
                for row in rows:
                    cursor.execute(
                        sql,
                        (
                            row["datetime"],
                            row["symbol"],
                            row["open"],
                            row["high"],
                            row["low"],
                            row["close"],
                            row.get("volume"),
                        ),
                    )
            conn.commit()
        return len(rows)

    def fetch_symbol_rows(self, table_name: str, symbol: str, page_size: int = 1000) -> List[Dict[str, Any]]:
        qualified = self._qualified_table(table_name)
        all_rows: List[Dict[str, Any]] = []
        offset = 0

        with self._connect() as conn:
            while True:
                with conn.cursor(as_dict=True) as cursor:
                    cursor.execute(
                        f"""
                        SELECT
                            CONVERT(varchar(10), [datetime], 23) AS [datetime],
                            [symbol], [open], [high], [low], [close], [volume]
                        FROM {qualified}
                        WHERE [symbol] = %s
                        ORDER BY [datetime]
                        OFFSET {int(offset)} ROWS FETCH NEXT {int(page_size)} ROWS ONLY
                        """,
                        (symbol,),
                    )
                    page = cursor.fetchall()
                if not page:
                    break
                all_rows.extend(page)
                if len(page) < page_size:
                    break
                offset += page_size
        return all_rows
