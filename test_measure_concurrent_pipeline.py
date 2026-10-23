import unittest
from unittest.mock import patch

from measure_concurrent_pipeline import measure_concurrent_pipeline


class TestMeasureConcurrentPipeline(unittest.TestCase):

    def test_reports_elapsed_time_and_throughput(self):
        summary = {"orders_processed": 10}

        with patch(
            "measure_concurrent_pipeline.run_concurrent",
            return_value=summary,
        ) as runner:
            with patch(
                "measure_concurrent_pipeline.perf_counter_ns",
                side_effect=[100, 1100],
            ):
                result = measure_concurrent_pipeline(
                    count=10,
                    seed=7,
                    capacity=2,
                    timeout=5,
                )

        self.assertEqual(result["elapsed_ns"], 1000)
        self.assertEqual(result["orders_per_second"], 10_000_000.0)
        self.assertEqual(result["summary"], summary)
        runner.assert_called_once_with(
            count=10,
            seed=7,
            capacity=2,
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()