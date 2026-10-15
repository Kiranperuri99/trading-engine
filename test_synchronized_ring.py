import multiprocessing
import tempfile
import unittest
from pathlib import Path

from ring_buffer import RingBuffer
from synchronized_ring import SynchronizedRing
from trading_engine import Order


class TestSynchronizedRing(unittest.TestCase):

    def test_wrapper_preserves_queue_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()
            order = Order(1, "BUY", 100.0, 5)

            with RingBuffer(path, 2) as ring:
                queue = SynchronizedRing(ring, lock)

                queue.put(order)
                self.assertEqual(len(queue), 1)
                self.assertEqual(queue.get(), order)
                self.assertEqual(len(queue), 0)

    def test_lock_is_released_after_empty_queue_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()

            with RingBuffer(path, 2) as ring:
                queue = SynchronizedRing(ring, lock)

                with self.assertRaises(BufferError):
                    queue.get()

                acquired = lock.acquire(timeout=1)
                try:
                    self.assertTrue(acquired)
                finally:
                    if acquired:
                        lock.release()
    def test_try_put_returns_false_when_full(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()
            first = Order(1, "BUY", 100.0, 5)
            second = Order(2, "SELL", 101.0, 3)

            with RingBuffer(path, 1) as ring:
                queue = SynchronizedRing(ring, lock)

                self.assertTrue(queue.try_put(first))
                self.assertFalse(queue.try_put(second))
                self.assertEqual(queue.get(), first)

                self.assertTrue(queue.try_put(second))
                self.assertEqual(queue.get(), second)

    def test_try_get_returns_none_when_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()
            order = Order(1, "BUY", 100.0, 5)

            with RingBuffer(path, 1) as ring:
                queue = SynchronizedRing(ring, lock)

                self.assertIsNone(queue.try_get())
                queue.put(order)
                self.assertEqual(queue.try_get(), order)
                self.assertIsNone(queue.try_get())

    def test_try_put_rejects_invalid_order_when_space_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()

            with RingBuffer(path, 1) as ring:
                queue = SynchronizedRing(ring, lock)

                with self.assertRaises(ValueError):
                    queue.try_put(Order(1, "BUY", 100.0, 0))

                self.assertEqual(len(queue), 0)

if __name__ == "__main__":
    unittest.main()