from benchmark_simulation import benchmark_simulation
from benchmark_concurrent import benchmark_concurrent
import unittest
from unittest.mock import patch

from benchmark_environment import benchmark_environment


class TestBenchmarkEnvironment(unittest.TestCase):
    def test_sequential_benchmark_includes_environment(self):
        expected = {"python_version": "test-version"}

        with patch(
            "benchmark_simulation.benchmark_environment",
            return_value=expected,
        ), patch(
            "benchmark_simulation.run_simulation",
            return_value={"orders_processed": 1},
        ), patch(
            "benchmark_simulation.perf_counter_ns",
            side_effect=[0, 1_000_000],
        ):
            result = benchmark_simulation(count=1)

        self.assertEqual(result["environment"], expected)

    def test_concurrent_benchmark_includes_environment(self):
        expected = {"python_version": "test-version"}

        with patch(
            "benchmark_concurrent.benchmark_environment",
            return_value=expected,
        ), patch(
            "benchmark_concurrent.run_concurrent",
            return_value={"orders_processed": 1},
        ), patch(
            "benchmark_concurrent.perf_counter_ns",
            side_effect=[0, 1_000_000],
        ):
            result = benchmark_concurrent(count=1)

        self.assertEqual(result["environment"], expected)

    def test_reports_environment_details(self):
        with patch(
            "benchmark_environment.platform.python_version",
            return_value="3.14.0",
        ), patch(
            "benchmark_environment.platform.python_implementation",
            return_value="CPython",
        ), patch(
            "benchmark_environment.platform.system",
            return_value="Windows",
        ), patch(
            "benchmark_environment.platform.release",
            return_value="11",
        ), patch(
            "benchmark_environment.platform.machine",
            return_value="AMD64",
        ), patch(
            "benchmark_environment.struct.calcsize",
            return_value=8,
        ):
            result = benchmark_environment()

        self.assertEqual(result, {
            "python_version": "3.14.0",
            "python_implementation": "CPython",
            "operating_system": "Windows",
            "os_release": "11",
            "machine": "AMD64",
            "pointer_bits": 64,
        })


if __name__ == "__main__":
    unittest.main()