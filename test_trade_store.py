import tempfile
import unittest
from pathlib import Path

from trade_store import SQLiteTradeStore


class TestSQLiteTradeStore(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
