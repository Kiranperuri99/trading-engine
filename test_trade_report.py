from trade_report import build_parser, main
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from trade_report import main
from trade_store import SQLiteTradeStore


class TestTradeReport(unittest.TestCase):
    def test_human_filter_shows_matching_trade(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "trades.db"

            with SQLiteTradeStore(database) as store:
                store.record_trade({
                    "buy_order_id": 1,
                    "sell_order_id": 2,
                    "price": 100.0,
                    "quantity": 5,
                })

            output = io.StringIO()
            with redirect_stdout(output):
                main(["--database", str(database), "--order-id", "1"])

            self.assertIn("Trades involving order ID 1", output.getvalue())
            self.assertIn("'sell_order_id': 2", output.getvalue())
    def test_parser_rejects_invalid_order_ids(self):
        parser = build_parser()

        for value in ("0", "-1", "abc"):
            with self.subTest(order_id=value):
                with self.assertRaises(SystemExit):
                    parser.parse_args([
                        "--database", "trades.db",
                        "--order-id", value,
                    ])
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

    def test_json_filter_returns_empty_list_for_unknown_order_id(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "trades.db"

            with SQLiteTradeStore(database) as store:
                store.record_trade({
                    "buy_order_id": 1,
                    "sell_order_id": 2,
                    "price": 100.0,
                    "quantity": 5,
                })

            output = io.StringIO()
            with redirect_stdout(output):
                main([
                    "--database", str(database),
                    "--order-id", "999",
                    "--json",
                ])

            self.assertEqual(json.loads(output.getvalue()), [])
if __name__ == "__main__":
    unittest.main()
