from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path))
        self._connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self._connection.close()

    def init_schema(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                barcode TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL CHECK(price > 0),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        self._connection.commit()

    def upsert_product(self, barcode: str, name: str, price: float) -> None:
        self._connection.execute(
            """
            INSERT INTO products(barcode, name, price, updated_at)
            VALUES(?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(barcode) DO UPDATE SET
                name = excluded.name,
                price = excluded.price,
                updated_at = datetime('now', 'localtime')
            """,
            (barcode, name, price),
        )
        self._connection.commit()

    def get_product_by_barcode(self, barcode: str) -> dict[str, Any] | None:
        cursor = self._connection.execute(
            "SELECT barcode, name, price FROM products WHERE barcode = ?",
            (barcode,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_products(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            cursor = self._connection.execute(
                """
                SELECT barcode, name, price
                FROM products
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

        cursor = self._connection.execute(
            """
            SELECT barcode, name, price
            FROM products
            WHERE barcode LIKE ? OR name LIKE ?
            ORDER BY
                CASE WHEN barcode LIKE ? THEN 0 ELSE 1 END,
                updated_at DESC
            LIMIT ?
            """,
            (f"{q}%", f"%{q}%", f"{q}%", limit),
        )
        return [dict(row) for row in cursor.fetchall()]
