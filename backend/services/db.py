from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def default_sqlite_path() -> str:
    # BASE_DIR is the backend/ folder
    BASE_DIR = Path(__file__).resolve().parent.parent
    path = BASE_DIR / "o2c.sqlite"
    print(f"Loading data from: {BASE_DIR}")
    return str(path)


def get_sqlite_path() -> str:
    return os.environ.get("SQLITE_PATH", default_sqlite_path())


@contextmanager
def sqlite_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(get_sqlite_path())
    try:
        yield conn
    finally:
        conn.close()

