import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from trade_report import main
from trade_store import SQLiteTradeStore


class TestTradeReport(unittest.TestCase):
    def test_json_output_can_filter_by_order_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"
            trade = {
                "buy_order_id": 1,
                "sell_order_id": 2,
                "price": 100.0,
                "quantity": 5,
            }

            with SQLiteTradeStore(path) as store:
                store.record_trade(trade)

            output = io.StringIO()
            with redirect_stdout(output):
                main([
                    "--database", str(path),
                    "--order-id", "1",
                    "--json",
                ])

            self.assertEqual(json.loads(output.getvalue()), [trade])
    def test_json_output_shows_saved_trade_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"
            trade = {
                "buy_order_id": 1,
                "sell_order_id": 2,
                "price": 100.0,
                "quantity": 5,
            }

            with SQLiteTradeStore(path) as store:
                store.record_trade(trade)

            output = io.StringIO()
            with redirect_stdout(output):
                main(["--database", str(path), "--json"])

            self.assertEqual(
                json.loads(output.getvalue()),
                {
                    "trade_count": 1,
                    "total_quantity": 5,
                    "vwap": 100.0,
                },
            )


if __name__ == "__main__":
    unittest.main()
