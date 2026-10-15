
import io
import json
from contextlib import redirect_stdout
from run_simulation import main
import argparse
from run_simulation import build_parser, non_negative_count
import unittest

from market_simulator import generate_orders
from run_simulation import run_simulation


class TestRunSimulation(unittest.TestCase):

    def test_summary_counts_all_orders_and_quantities(self):
        count = 37
        seed = 42
        submitted = sum(
            order.quantity
            for order in generate_orders(count, seed)
        )

        result = run_simulation(count, seed)

        self.assertEqual(result["orders_processed"], count)
        self.assertEqual(
            submitted,
            result["pending_buy_quantity"]
            + result["pending_sell_quantity"]
            + 2 * result["traded_quantity"],
        )

    def test_empty_simulation_returns_empty_summary(self):
        result = run_simulation(0)

        self.assertEqual(result["orders_processed"], 0)
        self.assertEqual(result["trade_count"], 0)
        self.assertEqual(result["traded_quantity"], 0)
        self.assertEqual(result["pending_buy_quantity"], 0)
        self.assertEqual(result["pending_sell_quantity"], 0)
        self.assertIsNone(result["best_bid"])
        self.assertIsNone(result["best_ask"])
        self.assertIsNone(result["spread"])
    def test_command_line_options(self):
        args = build_parser().parse_args(
            ["--count", "37", "--seed", "7"]
        )

        self.assertEqual(args.count, 37)
        self.assertEqual(args.seed, 7)

    def test_command_line_defaults(self):
        args = build_parser().parse_args([])

        self.assertEqual(args.count, 100)
        self.assertEqual(args.seed, 42)

    def test_invalid_command_line_counts_are_rejected(self):
        for value in ("-1", "2.5", "hello", str(1 << 64)):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    non_negative_count(value)
    def test_json_output_matches_simulation_summary(self):
        output = io.StringIO()

        with redirect_stdout(output):
            main(["--count", "37", "--seed", "7", "--json"])

        result = json.loads(output.getvalue())

        self.assertEqual(result, run_simulation(37, 7))

    def test_empty_json_output_uses_null_for_missing_prices(self):
        output = io.StringIO()

        with redirect_stdout(output):
            main(["--count", "0", "--json"])

        result = json.loads(output.getvalue())

        self.assertEqual(result["orders_processed"], 0)
        self.assertIsNone(result["best_bid"])
        self.assertIsNone(result["best_ask"])
        self.assertIsNone(result["spread"])
if __name__ == "__main__":
    unittest.main()