import json
import io
from contextlib import redirect_stdout
from measure_engine_latency import build_parser, main
import unittest
from unittest.mock import patch

from measure_engine_latency import measure_engine_latency
from run_simulation import run_simulation


class TestMeasureEngineLatency(unittest.TestCase):
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
        })
        self.assertEqual(result["latency"]["count"], 2)
        self.assertEqual(result["latency"]["median_ns"], 20.0)
        self.assertEqual(result["latency"]["p95_ns"], 30)
        self.assertEqual(result["summary"]["orders_processed"], 2)

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

        measurement.assert_called_once_with(count=25, seed=7)
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


if __name__ == "__main__":
    unittest.main()