import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from benchmark_matchers import (
    CythonMatchCore,
    benchmark_matchers,
    build_parser,
    main,
)
from trading_engine import ChronosMatch


class TestBenchmarkMatchers(unittest.TestCase):
    def test_benchmark_reports_medians_and_speedup_for_equal_engines(self):
        ticks = iter((0, 10, 20, 50, 100, 130, 200, 240))
        with patch("benchmark_matchers.CythonMatchCore", ChronosMatch):
            with patch("benchmark_matchers.perf_counter_ns", side_effect=lambda: next(ticks)):
                result = benchmark_matchers(
                    count=2,
                    seed=7,
                    repeats=2,
                    warmup=0,
                )

        self.assertEqual(result["configuration"], {
            "mode": "matching-core",
            "count": 2,
            "seed": 7,
            "repeats": 2,
            "warmup": 0,
        })
        self.assertEqual(result["results"]["python"]["samples_ns"], [10, 40])
        self.assertEqual(result["results"]["python"]["min_elapsed_ns"], 10)
        self.assertEqual(result["results"]["python"]["median_elapsed_ns"], 25)
        self.assertEqual(result["results"]["python"]["max_elapsed_ns"], 40)
        self.assertEqual(result["results"]["cython"]["samples_ns"], [30, 30])
        self.assertEqual(result["results"]["cython"]["min_elapsed_ns"], 30)
        self.assertEqual(result["results"]["cython"]["median_elapsed_ns"], 30)
        self.assertEqual(result["results"]["cython"]["max_elapsed_ns"], 30)
        self.assertEqual(result["median_time_difference_ns"], -5)
        self.assertEqual(result["schema_version"], 2)
        self.assertAlmostEqual(result["cython_speedup_ratio"], 25 / 30)

    def test_benchmark_rejects_non_positive_workload_values(self):
        with patch("benchmark_matchers.CythonMatchCore", ChronosMatch):
            with self.assertRaisesRegex(ValueError, "Order count"):
                benchmark_matchers(count=0)
            with self.assertRaisesRegex(ValueError, "Repeat count"):
                benchmark_matchers(repeats=0)
            with self.assertRaisesRegex(ValueError, "Warm-up count"):
                benchmark_matchers(warmup=-1)

    def test_benchmark_requires_built_cython_extension(self):
        with patch("benchmark_matchers.CythonMatchCore", None):
            with self.assertRaisesRegex(RuntimeError, "build it with"):
                benchmark_matchers(count=1, warmup=0, repeats=1)

    def test_benchmark_report_includes_utc_generation_timestamp(self):
        ticks = iter((0, 10, 20, 30))
        with patch("benchmark_matchers.CythonMatchCore", ChronosMatch):
            with patch("benchmark_matchers.perf_counter_ns", side_effect=lambda: next(ticks)):
                result = benchmark_matchers(count=1, repeats=1, warmup=0)

        timestamp = datetime.fromisoformat(result["generated_at_utc"])
        self.assertIsNotNone(timestamp.tzinfo)
        self.assertEqual(timestamp.utcoffset().total_seconds(), 0)

    def test_parser_defaults_and_custom_values(self):
        defaults = build_parser().parse_args([])
        self.assertEqual(defaults.count, 1000)
        self.assertEqual(defaults.seed, 42)
        self.assertEqual(defaults.repeats, 5)
        self.assertEqual(defaults.warmup, 1)
        self.assertIsNone(defaults.minimum_speedup_ratio)
        self.assertFalse(defaults.fail_on_speedup_miss)

        selected = build_parser().parse_args([
            "--count", "200",
            "--seed", "7",
            "--repeats", "3",
            "--warmup", "0",
            "--minimum-speedup-ratio", "1.25",
            "--json",
        ])
        self.assertEqual(selected.count, 200)
        self.assertEqual(selected.seed, 7)
        self.assertEqual(selected.repeats, 3)
        self.assertEqual(selected.warmup, 0)
        self.assertEqual(selected.minimum_speedup_ratio, 1.25)
        self.assertTrue(selected.json)

    def test_minimum_speedup_ratio_rejects_non_positive_or_non_finite_values(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value):
                with patch("sys.stderr", io.StringIO()):
                    with self.assertRaises(SystemExit):
                        build_parser().parse_args([
                            "--minimum-speedup-ratio", value,
                        ])

    def test_parser_accepts_csv_output(self):
        args = build_parser().parse_args([
            "--csv-output", "matcher-timings.csv",
            "--output", "matcher-report.json",
        ])

        self.assertEqual(args.csv_output, Path("matcher-timings.csv"))
        self.assertEqual(args.output, Path("matcher-report.json"))

    def test_json_output_saves_complete_report_to_file(self):
        result = {
            "schema_version": 2,
            "configuration": {"count": 1},
            "environment": {},
            "results": {},
            "median_time_difference_ns": 0,
            "cython_speedup_ratio": 1.0,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matcher-report.json"
            with patch("benchmark_matchers.benchmark_matchers", return_value=result):
                with redirect_stdout(io.StringIO()):
                    main(["--output", str(path)])

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)

    def test_json_and_csv_outputs_reject_the_same_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matcher-report.json"
            error_output = io.StringIO()
            with patch("sys.stderr", error_output):
                with self.assertRaises(SystemExit) as raised:
                    main([
                        "--output", str(path),
                        "--csv-output", str(path.parent / "." / path.name),
                    ])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("must use different file paths", error_output.getvalue())
        self.assertFalse(path.exists())

    def test_csv_output_saves_each_measured_matcher_run(self):
        result = {
            "schema_version": 2,
            "configuration": {
                "count": 100,
                "seed": 7,
                "repeats": 2,
                "warmup": 1,
            },
            "generated_at_utc": "2026-11-01T12:00:00+00:00",
            "environment": {
                "python_version": "3.14.7",
                "python_implementation": "CPython",
                "operating_system": "Windows",
                "os_release": "11",
                "machine": "AMD64",
                "pointer_bits": 64,
            },
            "results": {
                "python": {
                    "samples_ns": [100, 0],
                    "trade_count": 3,
                    "traded_quantity": 25,
                    "pending_quantities": {"BUY": 4, "SELL": 5},
                },
                "cython": {
                    "samples_ns": [50, 100],
                    "trade_count": 3,
                    "traded_quantity": 25,
                    "pending_quantities": {"BUY": 4, "SELL": 5},
                },
            },
            "cython_speedup_ratio": 2.0,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matcher-timings.csv"
            with patch("benchmark_matchers.benchmark_matchers", return_value=result):
                with redirect_stdout(io.StringIO()):
                    main([
                        "--csv-output", str(path),
                        "--minimum-speedup-ratio", "1.2",
                        "--json",
                    ])

            with path.open(newline="", encoding="utf-8") as input_file:
                rows = list(csv.reader(input_file))

        self.assertEqual(rows, [
            [
                "schema_version",
                "matcher",
                "run_number",
                "elapsed_ns",
                "orders_per_second",
                "paired_speedup_ratio",
                "generated_at_utc",
                "python_version",
                "python_implementation",
                "operating_system",
                "os_release",
                "machine",
                "pointer_bits",
                "order_count",
                "seed",
                "measured_repeats",
                "warmup_runs",
                "trade_count",
                "traded_quantity",
                "pending_buy_quantity",
                "pending_sell_quantity",
                "minimum_speedup_ratio",
                "minimum_speedup_met",
            ],
            [
                "2", "python", "1", "100", "1000000000.0",
                "2.0",
                "2026-11-01T12:00:00+00:00",
                "3.14.7", "CPython", "Windows", "11", "AMD64", "64",
                "100", "7", "2", "1",
                "3", "25", "4", "5", "1.2", "true",
            ],
            [
                "2", "python", "2", "0", "",
                "0.0",
                "2026-11-01T12:00:00+00:00",
                "3.14.7", "CPython", "Windows", "11", "AMD64", "64",
                "100", "7", "2", "1",
                "3", "25", "4", "5", "1.2", "true",
            ],
            [
                "2", "cython", "1", "50", "2000000000.0",
                "2.0",
                "2026-11-01T12:00:00+00:00",
                "3.14.7", "CPython", "Windows", "11", "AMD64", "64",
                "100", "7", "2", "1",
                "3", "25", "4", "5", "1.2", "true",
            ],
            [
                "2", "cython", "2", "100", "1000000000.0",
                "0.0",
                "2026-11-01T12:00:00+00:00",
                "3.14.7", "CPython", "Windows", "11", "AMD64", "64",
                "100", "7", "2", "1",
                "3", "25", "4", "5", "1.2", "true",
            ],
        ])

    def test_csv_output_does_not_overwrite_existing_file(self):
        result = {
            "configuration": {
                "count": 1,
                "seed": 42,
                "repeats": 1,
                "warmup": 0,
            },
            "generated_at_utc": "2026-11-01T12:00:00+00:00",
            "environment": {},
            "results": {
                "python": {"samples_ns": [100]},
                "cython": {"samples_ns": [50]},
            },
            "cython_speedup_ratio": 2.0,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matcher-timings.csv"
            path.write_text("keep", encoding="utf-8")
            with patch("benchmark_matchers.benchmark_matchers", return_value=result):
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(FileExistsError):
                        main(["--csv-output", str(path)])

            self.assertEqual(path.read_text(encoding="utf-8"), "keep")

    def test_json_output_is_valid(self):
        output = io.StringIO()
        result = {
            "configuration": {"count": 1},
            "environment": {},
            "results": {},
            "cython_speedup_ratio": 1.0,
        }
        with patch("benchmark_matchers.benchmark_matchers", return_value=result):
            with redirect_stdout(output):
                main(["--json"])

        self.assertIn('"cython_speedup_ratio": 1.0', output.getvalue())

    def test_minimum_speedup_check_is_in_json_report(self):
        for measured_ratio, minimum_ratio, expected in (
            (1.5, 1.25, True),
            (0.9, 1.0, False),
            (None, 1.0, False),
        ):
            with self.subTest(measured_ratio=measured_ratio):
                output = io.StringIO()
                result = {"cython_speedup_ratio": measured_ratio}
                with patch(
                    "benchmark_matchers.benchmark_matchers",
                    return_value=result,
                ):
                    with redirect_stdout(output):
                        main([
                            "--minimum-speedup-ratio",
                            str(minimum_ratio),
                            "--json",
                        ])

                report = json.loads(output.getvalue())
                self.assertEqual(
                    report["minimum_speedup_check"],
                    {"minimum_ratio": minimum_ratio, "met": expected},
                )

    def test_fail_on_speedup_miss_returns_failure_only_when_threshold_is_missed(self):
        for measured_ratio, expected_status in ((1.5, 0), (0.9, 1), (None, 1)):
            with self.subTest(measured_ratio=measured_ratio):
                output = io.StringIO()
                result = {"cython_speedup_ratio": measured_ratio}
                with patch(
                    "benchmark_matchers.benchmark_matchers",
                    return_value=result,
                ):
                    with redirect_stdout(output):
                        status = main([
                            "--minimum-speedup-ratio", "1.0",
                            "--fail-on-speedup-miss",
                            "--json",
                        ])

                self.assertEqual(status, expected_status)
                report = json.loads(output.getvalue())
                self.assertEqual(
                    report["minimum_speedup_check"]["met"],
                    expected_status == 0,
                )

    def test_fail_on_speedup_miss_requires_a_threshold(self):
        with patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["--fail-on-speedup-miss"])

        self.assertEqual(raised.exception.code, 2)

    def test_text_report_includes_minimum_and_maximum_elapsed_times(self):
        result = {
            "results": {
                "python": {
                    "min_elapsed_ns": 10,
                    "median_elapsed_ns": 15,
                    "max_elapsed_ns": 20,
                    "orders_per_second": 1.0,
                    "median_ns_per_order": 1.0,
                },
                "cython": {
                    "min_elapsed_ns": 5,
                    "median_elapsed_ns": 8,
                    "max_elapsed_ns": 12,
                    "orders_per_second": 2.0,
                    "median_ns_per_order": 0.5,
                },
            },
            "median_time_difference_ns": -2,
            "cython_speedup_ratio": 2.0,
        }
        output = io.StringIO()
        with patch("benchmark_matchers.benchmark_matchers", return_value=result):
            with redirect_stdout(output):
                main(["--minimum-speedup-ratio", "1.5"])

        self.assertIn("python: min_elapsed_ns=10", output.getvalue())
        self.assertIn("python: max_elapsed_ns=20", output.getvalue())
        self.assertIn("cython: min_elapsed_ns=5", output.getvalue())
        self.assertIn("cython: max_elapsed_ns=12", output.getvalue())
        self.assertIn("python_minus_cython_median_ns: -2", output.getvalue())
        self.assertIn("minimum_speedup_check: PASS", output.getvalue())

    @unittest.skipIf(
        CythonMatchCore is None,
        "Build the Cython extension to run the matcher parity benchmark",
    )
    def test_benchmark_runs_real_matchers_and_confirms_parity(self):
        result = benchmark_matchers(count=80, seed=9, repeats=1, warmup=0)

        python_result = result["results"]["python"]
        cython_result = result["results"]["cython"]
        for field in (
            "trade_count",
            "traded_quantity",
            "pending_quantities",
        ):
            with self.subTest(field=field):
                self.assertEqual(python_result[field], cython_result[field])

        self.assertGreater(python_result["median_elapsed_ns"], 0)
        self.assertGreater(cython_result["median_elapsed_ns"], 0)


if __name__ == "__main__":
    unittest.main()