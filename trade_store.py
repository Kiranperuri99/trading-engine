import sqlite3


class SQLiteTradeStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
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
        self.connection.commit()

    def record_trade(self, trade):
        self.connection.execute(
            """
            INSERT INTO trades (buy_order_id, sell_order_id, price, quantity)
            VALUES (?, ?, ?, ?)
            """,
            (
                trade["buy_order_id"],
                trade["sell_order_id"],
                trade["price"],
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
    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
