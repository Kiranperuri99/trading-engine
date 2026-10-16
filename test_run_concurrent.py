
from time import sleep
from unittest.mock import patch
import unittest

from run_concurrent import run_concurrent
from run_simulation import run_simulation
def failing_producer(*args):
    raise RuntimeError("Deliberate worker failure for testing")


def stalled_worker(*args):
    sleep(10)


class TestRunConcurrent(unittest.TestCase):
    def test_failed_producer_is_reported(self):
        with patch(
            "run_concurrent.producer_process",
            new=failing_producer,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "producer failed with exit code",
            ):
                run_concurrent(
                    count=1,
                    capacity=1,
                    timeout=15,
                )

    def test_stalled_workers_trigger_parent_timeout(self):
        with patch(
            "run_concurrent.producer_process",
            new=stalled_worker,
        ):
            with patch(
                "run_concurrent.consumer_process",
                new=stalled_worker,
            ):
                with self.assertRaisesRegex(
                    TimeoutError,
                    "Concurrent simulation timed out",
                ):
                    run_concurrent(
                        count=1,
                        capacity=1,
                        timeout=1,
                    )

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