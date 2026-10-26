import tempfile
import unittest
from pathlib import Path

from trade_store import SQLiteTradeStore
from trading_engine import ChronosMatch, Order


class TestTradeStoreIntegration(unittest.TestCase):
    def test_engine_saves_completed_trade_to_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                engine = ChronosMatch(verbose=False, trade_store=store)
                engine.add_order(Order(1, "BUY", 101.0, 10))
                engine.add_order(Order(2, "SELL", 100.0, 5))

                expected = [{
                    "buy_order_id": 1,
                    "sell_order_id": 2,
                    "price": 101.0,
                    "quantity": 5,
                }]
                self.assertEqual(store.get_trades(), expected)
                self.assertEqual(engine.trades, expected)


if __name__ == "__main__":
    unittest.main()
