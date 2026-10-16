import unittest

from run_concurrent import run_concurrent
from run_simulation import run_simulation


class TestRunConcurrent(unittest.TestCase):

    def test_concurrent_results_match_sequential_results(self):
        expected = run_simulation(count=37, seed=7)

        result = run_concurrent(
            count=37,
            seed=7,
            capacity=4,
            timeout=30,
        )

        self.assertEqual(result, expected)

    def test_empty_concurrent_simulation(self):
        result = run_concurrent(
            count=0,
            capacity=1,
            timeout=30,
        )

        self.assertEqual(result, run_simulation(count=0))


if __name__ == "__main__":
    unittest.main()