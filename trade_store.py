
import sqlite3
from pathlib import Path
from math import isfinite
import sqlite3


class SQLiteTradeStore:
    def get_trade_summary_for_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        trade_count, total_quantity, total_notional = self.connection.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(quantity), 0),
                   COALESCE(SUM(price * quantity), 0)
            FROM trades
            WHERE buy_order_id = ? OR sell_order_id = ?
            """,
            (order_id, order_id),
        ).fetchone()

        vwap = total_notional / total_quantity if total_quantity else None

        return {
            "trade_count": trade_count,
            "total_quantity": total_quantity,
            "vwap": vwap,
        }
    def get_trade_summary_for_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        trade_count, total_quantity, total_notional = self.connection.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(quantity), 0),
                COALESCE(SUM(price * quantity), 0)
            FROM trades
            WHERE buy_order_id = ? OR sell_order_id = ?
            """,
            (order_id, order_id),
        ).fetchone()

        vwap = (
            total_notional / total_quantity
            if total_quantity
            else None
        )

        return {
            "trade_count": trade_count,
            "total_quantity": total_quantity,
            "vwap": vwap,
        }
    def __init__(self, path):
        database_path = Path(path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buy_order_id INTEGER NOT NULL,
                sell_order_id INTEGER NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_buy_order_id "
            "ON trades (buy_order_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_sell_order_id "
            "ON trades (sell_order_id)"
        )
    def record_trade(self, trade):
        required = ("buy_order_id", "sell_order_id", "price", "quantity")
        if not isinstance(trade, dict) or any(key not in trade for key in required):
            raise ValueError("Trade is missing required fields")

        for key in ("buy_order_id", "sell_order_id", "quantity"):
            if type(trade[key]) is not int or trade[key] <= 0:
                raise ValueError(f"{key} must be a positive integer")

        price = trade["price"]
        if type(price) not in (int, float):
            raise ValueError("Trade price must be a number")

        try:
            valid_price = isfinite(price) and price > 0
        except OverflowError:
            valid_price = False

        if not valid_price:
            raise ValueError("Trade price must be finite and greater than zero")

        self.connection.execute(
            """
            INSERT INTO trades (buy_order_id, sell_order_id, price, quantity)
            VALUES (?, ?, ?, ?)
            """,
            (
                trade["buy_order_id"],
                trade["sell_order_id"],
                price,
                trade["quantity"],
            ),
        )
        self.connection.commit()
    def get_trades(self):
        rows = self.connection.execute(
            """
            SELECT buy_order_id, sell_order_id, price, quantity
            FROM trades
            ORDER BY id
            """
        ).fetchall()

        return [
            {
                "buy_order_id": row[0],
                "sell_order_id": row[1],
                "price": row[2],
                "quantity": row[3],
            }
            for row in rows
        ]
    def get_trades_for_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        rows = self.connection.execute(
            """
            SELECT buy_order_id, sell_order_id, price, quantity
            FROM trades
            WHERE buy_order_id = ? OR sell_order_id = ?
            ORDER BY id
            """,
            (order_id, order_id),
        ).fetchall()

        return [
            {
                "buy_order_id": row[0],
                "sell_order_id": row[1],
                "price": row[2],
                "quantity": row[3],
            }
            for row in rows
        ]
    def get_trade_summary(self):
        trade_count, total_quantity, total_notional = self.connection.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(quantity), 0),
                COALESCE(SUM(price * quantity), 0)
            FROM trades
            """
        ).fetchone()

        vwap = (
            total_notional / total_quantity
            if total_quantity
            else None
        )

        return {
            "trade_count": trade_count,
            "total_quantity": total_quantity,
            "vwap": vwap,
        }
    def get_trade_summary_for_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        trade_count, total_quantity, total_notional = self.connection.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(quantity), 0),
                COALESCE(SUM(price * quantity), 0)
            FROM trades
            WHERE buy_order_id = ? OR sell_order_id = ?
            """,
            (order_id, order_id),
        ).fetchone()

        vwap = total_notional / total_quantity if total_quantity else None
        return {
            "trade_count": trade_count,
            "total_quantity": total_quantity,
            "vwap": vwap,
        }    
    def get_trade_summary_for_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        trade_count, total_quantity, total_value = self.connection.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(quantity), 0),
                   COALESCE(SUM(price * quantity), 0)
            FROM trades
            WHERE buy_order_id = ? OR sell_order_id = ?
            """,
            (order_id, order_id),
        ).fetchone()

        vwap = total_value / total_quantity if total_quantity else None

        return {
            "trade_count": trade_count,
            "total_quantity": total_quantity,
            "vwap": vwap,
        }

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
