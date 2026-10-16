import unittest
from unittest.mock import patch

from benchmark_environment import benchmark_environment


class TestBenchmarkEnvironment(unittest.TestCase):

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