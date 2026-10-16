import unittest
from unittest.mock import patch

from benchmark_concurrent import benchmark_concurrent


class TestBenchmarkConcurrent(unittest.TestCase):

    def test_calculates_rate_and_passes_worker_settings(self):
        with patch(
            "benchmark_concurrent.perf_counter_ns",
            side_effect=[1_000_000_000, 3_000_000_000],
        ):
            with patch(
                "benchmark_concurrent.run_concurrent",
                return_value={"orders_processed": 100},
            ) as runner:
                result = benchmark_concurrent(
                    count=100,
                    seed=7,
                    capacity=4,
                    timeout=20,
                )

        runner.assert_called_once_with(
            count=100, seed=7, capacity=4, timeout=20
        )
        self.assertEqual(result["elapsed_ns"], 2_000_000_000)
        self.assertEqual(result["orders_per_second"], 50.0)
        self.assertEqual(
            result["average_ns_per_order"], 20_000_000.0
        )

    def test_zero_orders_have_no_per_order_average(self):
        with patch(
            "benchmark_concurrent.perf_counter_ns",
            side_effect=[0, 1_000_000_000],
        ):
            with patch(
                "benchmark_concurrent.run_concurrent",
                return_value={"orders_processed": 0},
            ):
                result = benchmark_concurrent(count=0)

        self.assertEqual(result["orders_per_second"], 0.0)
        self.assertIsNone(result["average_ns_per_order"])


if __name__ == "__main__":
    unittest.main()