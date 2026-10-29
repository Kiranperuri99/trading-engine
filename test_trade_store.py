from math import isfinite
import sqlite3
import tempfile
import unittest
from pathlib import Path

from trade_store import SQLiteTradeStore


class TestSQLiteTradeStore(unittest.TestCase):
    def test_get_trades_for_order_respects_limit(self):
        with SQLiteTradeStore(":memory:") as store:
            first_trade = {
                "buy_order_id": 7,
                "sell_order_id": 1,
                "price": 100.0,
                "quantity": 2,
            }
            store.record_trade(first_trade)
            store.record_trade({
                "buy_order_id": 2,
                "sell_order_id": 7,
                "price": 110.0,
                "quantity": 3,
            })

            self.assertEqual(
                store.get_trades_for_order(7, limit=1),
                [first_trade],
            )

    def test_get_trades_for_order_rejects_invalid_limit(self):
        with SQLiteTradeStore(":memory:") as store:
            for limit in (0, -1, 1.5, "1", True):
                with self.subTest(limit=limit):
                    with self.assertRaises(ValueError):
                        store.get_trades_for_order(7, limit=limit)
    def test_order_summary_includes_buyer_and_seller_trades(self):
        with SQLiteTradeStore(":memory:") as store:
            store.record_trade({
                "buy_order_id": 7,
                "sell_order_id": 1,
                "price": 100.0,
                "quantity": 2,
            })
            store.record_trade({
                "buy_order_id": 2,
                "sell_order_id": 7,
                "price": 110.0,
                "quantity": 3,
            })

            self.assertEqual(
                store.get_trade_summary_for_order(7),
                {
                    "trade_count": 2,
                    "total_quantity": 5,
                    "vwap": 106.0,
                },
            )
    def test_order_summary_rejects_invalid_order_ids(self):
        with SQLiteTradeStore(":memory:") as store:
            for order_id in (0, -1, 1.5, "1", True, None):
                with self.subTest(order_id=order_id):
                    with self.assertRaises(ValueError):
                        store.get_trade_summary_for_order(order_id)
    def test_order_summary_is_empty_when_order_has_no_trades(self):
        with SQLiteTradeStore(":memory:") as store:
            self.assertEqual(
                store.get_trade_summary_for_order(999),
                {
                    "trade_count": 0,
                    "total_quantity": 0,
                    "vwap": None,
                },
            )
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
    def test_context_manager_closes_database_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"
            store = SQLiteTradeStore(path)
            connection = store.connection

            with store:
                pass

            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

    def test_order_lookup_rejects_invalid_order_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                for order_id in (0, -1, 1.5, True, "1", None):
                    with self.subTest(order_id=order_id):
                        with self.assertRaises(ValueError):
                            store.get_trades_for_order(order_id)
    def test_order_lookup_indexes_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                indexes = {
                    row[1]
                    for row in store.connection.execute(
                        "PRAGMA index_list(trades)"
                    )
                }

    def test_empty_database_has_empty_trade_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                self.assertEqual(
                    store.get_trade_summary(),
                    {
                        "trade_count": 0,
                        "total_quantity": 0,
                        "vwap": None,
                    },
                )

    def test_trade_summary_calculates_quantity_and_vwap(self):
        trades = [
            {
                "buy_order_id": 1,
                "sell_order_id": 2,
                "price": 100.0,
                "quantity": 2,
            },
            {
                "buy_order_id": 3,
                "sell_order_id": 4,
                "price": 110.0,
                "quantity": 1,
            },
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                for trade in trades:
                    store.record_trade(trade)

                self.assertEqual(
                    store.get_trade_summary(),
                    {
                        "trade_count": 2,
                        "total_quantity": 3,
                        "vwap": 310 / 3,
                    },
                )
    def test_invalid_trade_is_rejected_without_saving(self):
        valid_trade = {
            "buy_order_id": 1,
            "sell_order_id": 2,
            "price": 100.0,
            "quantity": 5,
        }
        invalid_trades = [
            {**valid_trade, "buy_order_id": 0},
            {**valid_trade, "sell_order_id": -1},
            {**valid_trade, "price": float("nan")},
            {**valid_trade, "quantity": 0},
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                for trade in invalid_trades:
                    with self.subTest(trade=trade):
                        with self.assertRaises(ValueError):
                            store.record_trade(trade)

                self.assertEqual(store.get_trades(), [])
    def test_find_trades_for_order_on_either_side(self):
        trades = [
            {
                "buy_order_id": 1,
                "sell_order_id": 2,
                "price": 100.0,
                "quantity": 5,
            },
            {
                "buy_order_id": 3,
                "sell_order_id": 1,
                "price": 101.0,
                "quantity": 2,
            },
            {
                "buy_order_id": 4,
                "sell_order_id": 5,
                "price": 99.0,
                "quantity": 1,
            },
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                for trade in trades:
                    store.record_trade(trade)

                self.assertEqual(
                    store.get_trades_for_order(1),
                    trades[:2],
                )
    def test_new_database_has_no_trades(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                self.assertEqual(store.get_trades(), [])

    def test_trade_is_saved_and_available_after_reopening(self):
        trade = {
            "buy_order_id": 1,
            "sell_order_id": 2,
            "price": 100.0,
            "quantity": 5,
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                store.record_trade(trade)
                self.assertEqual(store.get_trades(), [trade])

            with SQLiteTradeStore(path) as store:
                self.assertEqual(store.get_trades(), [trade])

    def test_find_trades_for_unknown_order_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                store.record_trade({
                    "buy_order_id": 1,
                    "sell_order_id": 2,
                    "price": 100.0,
                    "quantity": 5,
                })

                self.assertEqual(store.get_trades_for_order(999), [])
if __name__ == "__main__":
    unittest.main()
