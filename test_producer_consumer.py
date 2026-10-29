import multiprocessing
import tempfile
import time
import unittest
from pathlib import Path

from ring_buffer import RingBuffer
from synchronized_ring import SynchronizedRing
from trading_engine import Order


def produce(path, lock):
    with lock:
        ring = RingBuffer.open_existing(path)

    with ring:
        queue = SynchronizedRing(ring, lock)
        deadline = time.monotonic() + 15

        for order_id in range(1, 101):
            order = Order(order_id, "BUY", 100.0, 1)

            while not queue.try_put(order):
                if time.monotonic() >= deadline:
                    raise TimeoutError("Producer timed out")
                time.sleep(0.001)


def consume(path, lock):
    with lock:
        ring = RingBuffer.open_existing(path)

    with ring:
        queue = SynchronizedRing(ring, lock)
        deadline = time.monotonic() + 15

        for expected_id in range(1, 101):
            while True:
                order = queue.try_get()

                if order is not None:
                    break

                if time.monotonic() >= deadline:
                    raise TimeoutError("Consumer timed out")
                time.sleep(0.001)

            expected = Order(expected_id, "BUY", 100.0, 1)
            if order != expected:
                raise AssertionError(
                    f"Expected {expected}, received {order}"
                )


class TestProducerConsumer(unittest.TestCase):

    def test_concurrent_transfer_preserves_all_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            context = multiprocessing.get_context("spawn")
            lock = context.Lock()
            started = []

            with RingBuffer(path, 4) as ring:
                processes = [
                    context.Process(
                        target=produce,
                        args=(str(path), lock),
                    ),
                    context.Process(
                        target=consume,
                        args=(str(path), lock),
                    ),
                ]

                try:
                    for process in processes:
                        process.start()
                        started.append(process)

                    for process in started:
                        process.join(timeout=25)
                        self.assertFalse(
                            process.is_alive(),
                            "Worker did not finish in time",
                        )
                        self.assertEqual(process.exitcode, 0)

                    self.assertEqual(len(ring), 0)

                finally:
                    for process in started:
                        if process.is_alive():
                            process.terminate()

                    for process in started:
                        process.join()
                        process.close()


if __name__ == "__main__":
    unittest.main() 