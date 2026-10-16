import multiprocessing
import tempfile
import unittest
from pathlib import Path
from time import monotonic

from ring_buffer import RingBuffer
from trading_engine import Order
from worker_config import make_deadline
from worker_queue import open_worker_queue


class TestWorkerQueue(unittest.TestCase):

    def test_worker_opens_and_reads_existing_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()
            order = Order(1, "BUY", 100.0, 5)

            with RingBuffer(path, 2) as ring:
                ring.put(order)

            deadline = make_deadline(10)

            with open_worker_queue(path, lock, deadline) as queue:
                self.assertEqual(queue.try_get_before(deadline), order)
                self.assertEqual(len(queue), 0)

            with RingBuffer.open_existing(path) as ring:
                self.assertEqual(len(ring), 0)

    def test_expired_deadline_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.bin"
            lock = multiprocessing.get_context("spawn").Lock()

            with self.assertRaises(TimeoutError):
                with open_worker_queue(
                    path, lock, monotonic() - 1
                ):
                    self.fail("Expired operation should not run")

            self.assertFalse(path.exists())

    def test_mapping_is_closed_when_worker_body_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()

            with RingBuffer(path, 2):
                pass

            with self.assertRaisesRegex(RuntimeError, "Worker failed"):
                with open_worker_queue(
                    path, lock, make_deadline(10)
                ) as queue:
                    mapping = queue._ring._storage.buffer
                    raise RuntimeError("Worker failed")

            self.assertTrue(mapping.closed)


if __name__ == "__main__":
    unittest.main()