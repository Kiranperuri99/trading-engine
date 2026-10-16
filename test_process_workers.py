import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from process_workers import producer_process, consumer_process
from ring_buffer import RingBuffer
from run_simulation import run_simulation


class TestProcessWorkers(unittest.TestCase):

    def test_worker_entries_save_correct_results(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            path = directory / "ring.bin"
            producer_result = directory / "producer.json"
            consumer_result = directory / "consumer.json"
            lock = multiprocessing.get_context("spawn").Lock()

            with RingBuffer(path, 5):
                pass

            producer_process(
                path, lock, 5, 7, 10, producer_result
            )
            consumer_process(
                path, lock, 5, 10, consumer_result
            )

            self.assertEqual(
                json.loads(producer_result.read_text(encoding="utf-8")),
                {"orders_produced": 5},
            )
            self.assertEqual(
                json.loads(consumer_result.read_text(encoding="utf-8")),
                run_simulation(count=5, seed=7),
            )

    def test_failed_worker_does_not_write_success_result(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            path = directory / "missing.bin"
            result_path = directory / "producer.json"
            lock = multiprocessing.get_context("spawn").Lock()

            with self.assertRaises(FileNotFoundError):
                producer_process(
                    path, lock, 1, 7, 10, result_path
                )

            self.assertFalse(result_path.exists())


if __name__ == "__main__":
    unittest.main()