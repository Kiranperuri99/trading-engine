from math import isfinite
import tempfile
import unittest
from pathlib import Path

from trade_store import SQLiteTradeStore


class TestSQLiteTradeStore(unittest.TestCase):
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
