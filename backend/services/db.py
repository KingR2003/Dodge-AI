from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def default_sqlite_path() -> str:
    # Keep default aligned with typical local run.
    return str(Path(__file__).resolve().parents[1] / "o2c.sqlite")


def get_sqlite_path() -> str:
    return os.environ.get("SQLITE_PATH", default_sqlite_path())


@contextmanager
def sqlite_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(get_sqlite_path())
    try:
        yield conn
    finally:
        conn.close()

