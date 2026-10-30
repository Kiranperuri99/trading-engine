import io
import unittest
from contextlib import redirect_stdout
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
        self.assertEqual(result["results"]["python"]["median_elapsed_ns"], 25)
        self.assertEqual(result["results"]["cython"]["samples_ns"], [30, 30])
        self.assertEqual(result["results"]["cython"]["median_elapsed_ns"], 30)
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

    def test_parser_defaults_and_custom_values(self):
        defaults = build_parser().parse_args([])
        self.assertEqual(defaults.count, 1000)
        self.assertEqual(defaults.seed, 42)
        self.assertEqual(defaults.repeats, 5)
        self.assertEqual(defaults.warmup, 1)

        selected = build_parser().parse_args([
            "--count", "200",
            "--seed", "7",
            "--repeats", "3",
            "--warmup", "0",
            "--json",
        ])
        self.assertEqual(selected.count, 200)
        self.assertEqual(selected.seed, 7)
        self.assertEqual(selected.repeats, 3)
        self.assertEqual(selected.warmup, 0)
        self.assertTrue(selected.json)

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

    @unittest.skipIf(
        CythonMatchCore is None,
        "Build the Cython extension to run the matcher parity benchmark",
    )
    def test_benchmark_runs_real_matchers_and_confirms_parity(self):
        result = benchmark_matchers(count=80, seed=9, repeats=1, warmup=0)

        self.assertEqual(
            result["results"]["python"]["trade_count"],
            result["results"]["cython"]["trade_count"],
        )
        self.assertGreater(result["results"]["python"]["median_elapsed_ns"], 0)
        self.assertGreater(result["results"]["cython"]["median_elapsed_ns"], 0)


if __name__ == "__main__":
    unittest.main()
