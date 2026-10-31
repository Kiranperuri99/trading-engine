from datetime import datetime
import json
from contextlib import redirect_stdout
from io import StringIO
from trading_engine import Order
import tempfile
from pathlib import Path
import json
import io
from contextlib import redirect_stdout
from measure_engine_latency import build_parser, main
import unittest
from unittest.mock import patch

from measure_engine_latency import measure_engine_latency
from run_simulation import run_simulation


class TestMeasureEngineLatency(unittest.TestCase):
    def test_include_samples_cli_adds_samples_to_json(self):
        orders = [Order(1, "BUY", 100.0, 1)]

        with patch(
            "measure_engine_latency.generate_orders",
            return_value=orders,
        ), patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 113],
        ), redirect_stdout(StringIO()) as output:
            main(["--count", "1", "--include-samples", "--json"])

        report = json.loads(output.getvalue())
        self.assertEqual(report["samples_ns"], [13])
    def test_include_samples_adds_each_order_latency(self):
        orders = [Order(1, "BUY", 100.0, 1)]

        with patch(
            "measure_engine_latency.generate_orders",
            return_value=orders,
        ), patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 113],
        ):
            result = measure_engine_latency(
                count=1,
                seed=7,
                include_samples=True,
            )

        self.assertEqual(result["samples_ns"], [13])

    def test_sample_callback_receives_completed_order_measurements(self):
        orders = [
            Order(1, "BUY", 100.0, 1),
            Order(2, "SELL", 101.0, 1),
        ]
        updates = []

        with patch(
            "measure_engine_latency.generate_orders",
            return_value=orders,
        ), patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 115, 200, 230],
        ):
            result = measure_engine_latency(
                count=2,
                on_sample=lambda *update: updates.append(update),
            )

        self.assertEqual(
            updates,
            [(15, 1, 2, "BUY"), (30, 2, 2, "SELL")],
        )
        self.assertEqual(result["latency"]["count"], 2)

    def test_order_sample_callback_includes_order_id(self):
        orders = [
            Order(51, "BUY", 100.0, 1),
            Order(72, "SELL", 101.0, 1),
        ]
        updates = []

        with patch(
            "measure_engine_latency.generate_orders",
            return_value=orders,
        ), patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 115, 200, 230],
        ):
            measure_engine_latency(
                count=2,
                on_order_sample=lambda *update: updates.append(update),
            )

        self.assertEqual(
            updates,
            [(15, 1, 2, "BUY", 51), (30, 2, 2, "SELL", 72)],
        )
    def test_json_report_has_utc_timestamp(self):
        with patch(
            "measure_engine_latency.generate_orders",
            return_value=[],
        ), redirect_stdout(StringIO()) as output:
            main(["--count", "0", "--json"])

        report = json.loads(output.getvalue())
        timestamp = datetime.fromisoformat(report["generated_at_utc"])

        self.assertIsNotNone(timestamp.tzinfo)
        self.assertEqual(timestamp.utcoffset().total_seconds(), 0)
    def test_json_output_includes_schema_version(self):
        with patch(
            "measure_engine_latency.generate_orders",
            return_value=[],
        ), redirect_stdout(StringIO()) as output:
            main(["--count", "0", "--json"])

        report = json.loads(output.getvalue())

        self.assertEqual(report["schema_version"], 1)
        self.assertIn("latency", report)
    def test_human_output_includes_engine_summary(self):
        result = {
            "scope": "ChronosMatch.add_order call",
            "configuration": {"count": 2, "seed": 7},
            "latency": {"count": 2, "median_ns": 20},
            "latency_by_side": {},
            "summary": {
                "orders_processed": 2,
                "trade_count": 1,
                "traded_quantity": 3,
            },
        }

        with patch(
            "measure_engine_latency.measure_engine_latency",
            return_value=result,
        ), redirect_stdout(StringIO()) as output:
            main(["--count", "2"])

        self.assertIn("Engine summary:", output.getvalue())
        self.assertIn("orders_processed: 2", output.getvalue())
        self.assertIn("trade_count: 1", output.getvalue())
    def test_output_option_saves_complete_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latency.json"
            output = io.StringIO()

            with redirect_stdout(output):
                main([
                    "--count", "0",
                    "--json",
                    "--output", str(path),
                ])

            saved = json.loads(path.read_text(encoding="utf-8"))
            printed = json.loads(output.getvalue())

            self.assertEqual(saved, printed)
            self.assertEqual(saved["latency"]["count"], 0)
            self.assertIn("environment", saved)

    def test_output_option_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latency.json"
            path.write_text("keep this", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                main(["--count", "0", "--output", str(path)])

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "keep this",
            )
    def test_measurement_includes_environment_outside_timed_calls(self):
        events = []

        def clock():
            events.append("clock")
            return len(events) * 10

        def environment():
            events.append("environment")
            return {"python_version": "test-version"}

        with patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=clock,
        ), patch(
            "measure_engine_latency.benchmark_environment",
            side_effect=environment,
        ):
            result = measure_engine_latency(count=1, seed=7)

        self.assertEqual(
            result["environment"],
            {"python_version": "test-version"},
        )
        self.assertEqual(events, ["clock", "clock", "environment"])
        self.assertEqual(result["latency"]["median_ns"], 10)
    def test_json_output_contains_measured_durations_and_summary(self):
        output = io.StringIO()

        with patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 110, 200, 230],
        ):
            with redirect_stdout(output):
                main(["--count", "2", "--seed", "7", "--json"])

        result = json.loads(output.getvalue())

        self.assertEqual(result["scope"], "ChronosMatch.add_order call")
        self.assertEqual(result["configuration"], {
            "count": 2,
            "seed": 7,
            "warmup": 0,
        })
        self.assertEqual(result["latency"]["count"], 2)
        self.assertEqual(result["latency"]["median_ns"], 20.0)
        self.assertEqual(result["latency"]["p95_ns"], 30)
        self.assertEqual(result["summary"]["orders_processed"], 2)
        self.assertEqual(result["throughput"]["measured_call_time_ns"], 40)
        self.assertEqual(result["throughput"]["orders_per_second"], 50_000_000)
        self.assertEqual(
            sum(
                stats["measured_call_time_ns"]
                for stats in result["throughput_by_side"].values()
            ),
            40,
        )

    def test_empty_json_output_has_null_latency_values(self):
        output = io.StringIO()

        with redirect_stdout(output):
            main(["--count", "0", "--json"])

        result = json.loads(output.getvalue())

        self.assertEqual(result["latency"]["count"], 0)
        self.assertIsNone(result["latency"]["median_ns"])
        self.assertIsNone(result["latency"]["p99_ns"])
    def test_cli_defaults(self):
        args = build_parser().parse_args([])

        self.assertEqual(args.count, 1000)
        self.assertEqual(args.seed, 42)

    def test_cli_passes_requested_count_and_seed(self):
        output = io.StringIO()

        with patch(
            "measure_engine_latency.measure_engine_latency",
            return_value={"latency": {"count": 25}},
        ) as measurement:
            with redirect_stdout(output):
                main(["--count", "25", "--seed", "7"])

        measurement.assert_called_once_with(count=25, seed=7, warmup=0, include_samples=False,)
        self.assertIn("count: 25", output.getvalue())

    def test_records_one_duration_per_order(self):
        with patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 110, 200, 230, 300, 320],
        ):
            result = measure_engine_latency(count=3, seed=7)

        self.assertEqual(result["latency"], {
            "count": 3,
            "min_ns": 10,
            "median_ns": 20,
            "p95_ns": 30,
            "p99_ns": 30,
            "p99_9_ns": 30,
            "max_ns": 30,
        })
        self.assertEqual(
            result["summary"],
            run_simulation(count=3, seed=7),
        )

    def test_empty_workload_has_no_timing_samples(self):
        with patch(
            "measure_engine_latency.perf_counter_ns"
        ) as clock:
            result = measure_engine_latency(count=0)

        clock.assert_not_called()
        self.assertEqual(result["latency"]["count"], 0)
        self.assertIsNone(result["latency"]["median_ns"])
        self.assertEqual(result["summary"]["orders_processed"], 0)
        self.assertEqual(result["throughput"]["measured_call_time_ns"], 0)
        self.assertIsNone(result["throughput"]["orders_per_second"])

    def test_human_output_includes_engine_call_throughput(self):
        output = io.StringIO()
        with patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 120],
        ):
            with redirect_stdout(output):
                result = main(["--count", "1", "--seed", "7"])

        self.assertEqual(result["throughput"]["orders_per_second"], 50_000_000)
        self.assertIn("Engine-call throughput", output.getvalue())
        self.assertIn("orders_per_second: 50000000.0", output.getvalue())
    def test_latency_is_reported_separately_for_each_side(self):
        orders = [
            Order(1, "BUY", 100.0, 1),
            Order(2, "SELL", 101.0, 1),
        ]

        with patch(
            "measure_engine_latency.generate_orders",
            return_value=orders,
        ), patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 110, 200, 230],
        ):
            result = measure_engine_latency(count=2, seed=7)

        self.assertEqual(result["latency_by_side"]["BUY"]["count"], 1)
        self.assertEqual(result["latency_by_side"]["BUY"]["min_ns"], 10)
        self.assertEqual(result["latency_by_side"]["SELL"]["count"], 1)
        self.assertEqual(result["latency_by_side"]["SELL"]["min_ns"], 30)
        self.assertEqual(
            result["throughput_by_side"]["BUY"]["measured_call_time_ns"], 10
        )
        self.assertEqual(
            result["throughput_by_side"]["BUY"]["orders_per_second"], 100_000_000
        )
        self.assertEqual(
            result["throughput_by_side"]["SELL"]["measured_call_time_ns"], 30
        )
        self.assertAlmostEqual(
            result["throughput_by_side"]["SELL"]["orders_per_second"],
            1_000_000_000 / 30,
        )
    def test_human_output_includes_latency_by_side(self):
        result = {
            "scope": "ChronosMatch.add_order call",
            "configuration": {"count": 2, "seed": 7},
            "latency": {"count": 2, "median_ns": 20},
            "latency_by_side": {
                "BUY": {"count": 1, "median_ns": 10},
                "SELL": {"count": 1, "median_ns": 30},
            },
            "summary": {},
        }

        with patch(
            "measure_engine_latency.measure_engine_latency",
            return_value=result,
        ), redirect_stdout(StringIO()) as output:
            main(["--count", "2"])

        self.assertIn("BUY order latency:", output.getvalue())
        self.assertIn("SELL order latency:", output.getvalue())
        self.assertIn("median_ns: 10", output.getvalue())
        self.assertIn("median_ns: 30", output.getvalue())
    def test_warmup_orders_are_excluded_from_report(self):
        orders = [Order(1, "BUY", 100.0, 1)]

        with patch(
            "measure_engine_latency.generate_orders",
            side_effect=[orders, orders],
        ) as generate, patch(
            "measure_engine_latency.perf_counter_ns",
            side_effect=[100, 110],
        ), redirect_stdout(StringIO()) as output:
            main(["--count", "1", "--seed", "7", "--warmup", "1", "--json"])

        report = json.loads(output.getvalue())

        self.assertEqual(report["latency"]["count"], 1)
        self.assertEqual(report["summary"]["orders_processed"], 1)
        generate.assert_any_call(1, 8)
        generate.assert_any_call(1, 7)

if __name__ == "__main__":
    unittest.main()
