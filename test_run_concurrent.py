
import subprocess
import sys
from pathlib import Path
import json
import argparse
import io
from contextlib import redirect_stdout
from run_concurrent import main, positive_capacity, positive_timeout
from time import sleep
from unittest.mock import patch
import unittest

from run_concurrent import run_concurrent
from run_simulation import non_negative_count, run_simulation
def failing_producer(*args):
    raise SystemExit(1)


def stalled_worker(*args):
    sleep(10)


class TestRunConcurrent(unittest.TestCase):
    def test_cli_shows_na_for_missing_market_prices(self):
        result = {
            "orders_processed": 0,
            "best_bid": None,
            "best_ask": None,
            "spread": None,
        }
        output = io.StringIO()

        with patch(
            "run_concurrent.run_concurrent",
            return_value=result,
        ):
            with redirect_stdout(output):
                main(["--count", "0"])

        self.assertIn("best_bid: N/A", output.getvalue())
        self.assertIn("best_ask: N/A", output.getvalue())
        self.assertIn("spread: N/A", output.getvalue())
    def test_cli_formats_market_prices(self):
        result = {
            "orders_processed": 3,
            "best_bid": 100.31,
            "best_ask": 100.47,
            "spread": 0.1599999999999966,
        }
        output = io.StringIO()

        with patch(
            "run_concurrent.run_concurrent",
            return_value=result,
        ):
            with redirect_stdout(output):
                main(["--count", "3"])

        self.assertIn("best_bid: 100.31", output.getvalue())
        self.assertIn("best_ask: 100.47", output.getvalue())
        self.assertIn("spread: 0.16", output.getvalue())
    def test_help_shows_descriptions_for_options(self):
        output = io.StringIO()

        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                main(["--help"])

        self.assertEqual(result.exception.code, 0)

        for description in (
            "Number of orders to generate and process.",
            "Seed used to generate repeatable orders.",
            "Maximum number of orders held in the ring buffer.",
            "Maximum time in seconds to wait for the workers.",
        ):
            self.assertIn(description, output.getvalue())
    def test_rejects_invalid_timeouts(self):
        for timeout in (0, -1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    run_concurrent(count=0, timeout=timeout)
    def test_rejects_invalid_ring_capacities(self):
        for capacity in (0, -1, True, 2.5, 1 << 64):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    run_concurrent(count=0, capacity=capacity)
    def test_cli_rejects_invalid_count(self):
        for value in ("-1", "2.5", "hello"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    non_negative_count(value)
    def test_concurrent_results_match_with_capacity_one(self):
        expected = run_simulation(count=100, seed=7)
        result = run_concurrent(
            count=100,
            seed=7,
            capacity=1,
            timeout=30,
        )
        self.assertEqual(result, expected)
    def test_script_prints_one_json_result(self):
        script = Path(__file__).with_name("run_concurrent.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--count",
                "0",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["orders_processed"], 0)
    def test_cli_json_output_is_valid_and_preserves_summary(self):
        expected = {
            "orders_processed": 0,
            "trade_count": 0,
            "traded_quantity": 0,
            "pending_buy_quantity": 0,
            "pending_sell_quantity": 0,
            "best_bid": None,
            "best_ask": None,
            "spread": None,
        }
        output = io.StringIO()

        with patch(
            "run_concurrent.run_concurrent",
            return_value=expected,
        ) as runner:
            with redirect_stdout(output):
                main(["--count", "0", "--json"])

        runner.assert_called_once_with(
            count=0,
            seed=42,
            capacity=16,
            timeout=30.0,
        )
        self.assertEqual(json.loads(output.getvalue()), expected)
    def test_cli_passes_selected_settings_to_runner(self):
        output = io.StringIO()

        with patch(
            "run_concurrent.run_concurrent",
            return_value={"orders_processed": 50},
        ) as runner:
            with redirect_stdout(output):
                main([
                    "--count", "50",
                    "--seed", "7",
                    "--capacity", "4",
                    "--timeout", "20",
                ])

        runner.assert_called_once_with(
            count=50,
            seed=7,
            capacity=4,
            timeout=20.0,
        )
        self.assertIn("orders_processed: 50", output.getvalue())

    def test_cli_rejects_invalid_capacity(self):
        for value in ("0", "-1", "2.5", "hello"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    positive_capacity(value)

    def test_cli_rejects_invalid_timeout(self):
        for value in ("0", "-1", "nan", "inf", "hello"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    positive_timeout(value)
    def test_failed_producer_is_reported(self):
        with patch(
            "run_concurrent.producer_process",
            new=failing_producer,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "producer failed with exit code",
            ):
                run_concurrent(
                    count=1,
                    capacity=1,
                    timeout=15,
                )

    def test_stalled_workers_trigger_parent_timeout(self):
        with patch(
            "run_concurrent.producer_process",
            new=stalled_worker,
        ):
            with patch(
                "run_concurrent.consumer_process",
                new=stalled_worker,
            ):
                with self.assertRaisesRegex(
                    TimeoutError,
                    "Concurrent simulation timed out",
                ):
                    run_concurrent(
                        count=1,
                        capacity=1,
                        timeout=1,
                    )

    def test_concurrent_results_match_sequential_results(self):
        expected = run_simulation(count=37, seed=7)

        result = run_concurrent(
            count=37,
            seed=7,
            capacity=4,
            timeout=30,
        )

        self.assertEqual(result, expected)
    def test_results_match_sequential_with_capacity_one(self):
        for seed in (0, 7, 42):
            with self.subTest(seed=seed):
                expected = run_simulation(count=25, seed=seed)
                actual = run_concurrent(
                    count=25,
                    seed=seed,
                    capacity=1,
                    timeout=30,
                )
                self.assertEqual(actual, expected)
    def test_rejects_invalid_order_counts(self):
        for count in (-1, True, 1.5, "5", 1 << 64):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    run_concurrent(count=count)
    def test_empty_concurrent_simulation(self):
        result = run_concurrent(
            count=0,
            capacity=1,
            timeout=30,
        )

        self.assertEqual(result, run_simulation(count=0))

    def test_runner_rejects_invalid_order_counts(self):
        for count in (-1, 1.5, True, 1 << 64):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    run_concurrent(count=count)
    def test_human_output_formats_market_prices(self):
        result = {
            "orders_processed": 0,
            "trade_count": 0,
            "traded_quantity": 0,
            "pending_buy_quantity": 0,
            "pending_sell_quantity": 0,
            "best_bid": 100.5,
            "best_ask": None,
            "spread": None,
        }
        output = io.StringIO()

        with patch(
            "run_concurrent.run_concurrent",
            return_value=result,
        ):
            with redirect_stdout(output):
                main([])

        text = output.getvalue()
        self.assertIn("best_bid: 100.50", text)
        self.assertIn("best_ask: N/A", text)
        self.assertIn("spread: N/A", text)
    def test_concurrent_simulation_handles_capacity_one(self):
        expected = run_simulation(count=25, seed=7)

        result = run_concurrent(
            count=25,
            seed=7,
            capacity=1,
            timeout=30,
        )

        self.assertEqual(result, expected)
    def test_runner_rejects_invalid_order_counts(self):
        for count in (-1, True, 1.5, "1", 1 << 64):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    run_concurrent(count=count)
    def test_runner_rejects_invalid_capacity_and_timeout(self):
        for capacity in (0, -1, True, 2.5):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    run_concurrent(count=0, capacity=capacity)

        for timeout in (0, -1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    run_concurrent(count=0, timeout=timeout)
if __name__ == "__main__":
    unittest.main()