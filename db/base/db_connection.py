"""
Shared SQLite connection utilities for db/ scripts.

Usage:
    with DBConnection(db_path) as db:
        db.execute("SELECT ...")
        db.batch_insert(sql, rows)      # executemany in chunks
        db.commit()                     # manual flush

Or just apply optimised PRAGMAs to an existing connection:
    conn = sqlite3.connect(db_path)
    apply_pragmas(conn)
"""

import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple, Any

_PRAGMAS = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA cache_size = -65536",    # 64 MB
    "PRAGMA temp_store = MEMORY",
    "PRAGMA mmap_size = 268435456",  # 256 MB
    "PRAGMA foreign_keys = ON",
]


def apply_pragmas(conn: sqlite3.Connection) -> None:
    """Apply performance PRAGMAs to an existing connection."""
    for pragma in _PRAGMAS:
        conn.execute(pragma)


class DBConnection:
    """
    Context manager for optimised SQLite connections.

    Applies performance PRAGMAs on enter, commits and closes on exit.
    Provides batch_insert() for bulk writes via executemany().
    """

    def __init__(self, db_path, batch_size: int = 500):
        self.db_path = Path(db_path)
        self.batch_size = batch_size
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Context manager

    def __enter__(self) -> "DBConnection":
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        apply_pragmas(self._conn)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn:
            if exc_type is None:
                self._conn.commit()
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Convenience wrappers

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("DBConnection used outside context manager")
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_iter) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params_iter)

    def commit(self) -> None:
        self.conn.commit()

    def fetchall(self, sql: str, params: tuple = ()) -> List[Any]:
        return self.conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> Any:
        return self.conn.execute(sql, params).fetchone()

    # ------------------------------------------------------------------
    # Batch helpers

    def batch_insert(
        self,
        sql: str,
        rows: List[Tuple],
        chunk_size: int | None = None,
    ) -> int:
        """
        Insert rows in chunks using executemany, committing after each chunk.

        Returns total number of rows inserted.
        """
        chunk = chunk_size or self.batch_size
        inserted = 0
        for i in range(0, len(rows), chunk):
            self.conn.executemany(sql, rows[i : i + chunk])
            self.conn.commit()
            inserted += min(chunk, len(rows) - i)
        return inserted

    def batch_update(
        self,
        sql: str,
        rows: List[Tuple],
        chunk_size: int | None = None,
    ) -> int:
        """Same as batch_insert but semantically for UPDATE statements."""
        return self.batch_insert(sql, rows, chunk_size)
