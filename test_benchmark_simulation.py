import io
from contextlib import redirect_stdout
from benchmark_simulation import build_parser, main
import unittest
from unittest.mock import patch

from benchmark_simulation import benchmark_simulation


class TestBenchmarkSimulation(unittest.TestCase):

    def test_benchmark_calculates_rate_and_average(self):
        with patch(
            "benchmark_simulation.perf_counter_ns",
            side_effect=[1_000_000_000, 3_000_000_000],
        ):
            with patch(
                "benchmark_simulation.run_simulation",
                return_value={"orders_processed": 100},
            ) as simulation:
                result = benchmark_simulation(100, 7)

        simulation.assert_called_once_with(count=100, seed=7)
        self.assertEqual(result["elapsed_ns"], 2_000_000_000)
        self.assertEqual(result["orders_per_second"], 50.0)
        self.assertEqual(result["average_ns_per_order"], 20_000_000.0)

    def test_empty_benchmark_has_no_per_order_average(self):
        with patch(
            "benchmark_simulation.perf_counter_ns",
            side_effect=[0, 1_000_000_000],
        ):
            with patch(
                "benchmark_simulation.run_simulation",
                return_value={"orders_processed": 0},
            ):
                result = benchmark_simulation(0)

        self.assertEqual(result["orders_per_second"], 0.0)
        self.assertIsNone(result["average_ns_per_order"])

    def test_benchmark_command_line_defaults(self):
        args = build_parser().parse_args([])

        self.assertEqual(args.count, 1000)
        self.assertEqual(args.seed, 42)

    def test_benchmark_command_line_passes_selected_values(self):
        output = io.StringIO()

        with patch(
            "benchmark_simulation.benchmark_simulation",
            return_value={"orders_processed": 200},
        ) as benchmark:
            with redirect_stdout(output):
                main(["--count", "200", "--seed", "7"])

        benchmark.assert_called_once_with(count=200, seed=7)
        self.assertIn("orders_processed: 200", output.getvalue())
if __name__ == "__main__":
    unittest.main()
