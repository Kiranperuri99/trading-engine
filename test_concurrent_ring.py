import multiprocessing
import tempfile
import unittest
from pathlib import Path

from ring_buffer import RingBuffer
from synchronized_ring import SynchronizedRing
from trading_engine import Order


def produce_orders(path, lock, start_event, first_id):
    if not start_event.wait(timeout=15):
        raise RuntimeError("Timed out waiting to start")

    # Opening validates the header, so protect that step too.
    with lock:
        ring = RingBuffer.open_existing(path)

    with ring:
        queue = SynchronizedRing(ring, lock)

        for order_id in range(first_id, first_id + 20):
            queue.put(Order(order_id, "BUY", 100.0, 1))


class TestConcurrentRing(unittest.TestCase):

    def test_two_producers_preserve_all_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            context = multiprocessing.get_context("spawn")
            lock = context.Lock()
            start_event = context.Event()
            started = []

            with RingBuffer(path, 40) as ring:
                processes = [
                    context.Process(
                        target=produce_orders,
                        args=(str(path), lock, start_event, first_id),
                    )
                    for first_id in (1, 101)
                ]

                try:
                    for process in processes:
                        process.start()
                        started.append(process)

                    start_event.set()

                    for process in started:
                        process.join(timeout=20)
                        self.assertFalse(
                            process.is_alive(),
                            "Producer did not finish in time",
                        )
                        self.assertEqual(process.exitcode, 0)

                    queue = SynchronizedRing(ring, lock)
                    self.assertEqual(len(queue), 40)

                    received = [queue.get() for _ in range(40)]
                    received_ids = [order.order_id for order in received]

                    self.assertEqual(
                        sorted(received_ids),
                        list(range(1, 21)) + list(range(101, 121)),
                    )

                    # Each producer's own arrival order is preserved.
                    self.assertEqual(
                        [value for value in received_ids if value < 100],
                        list(range(1, 21)),
                    )
                    self.assertEqual(
                        [value for value in received_ids if value >= 100],
                        list(range(101, 121)),
                    )
                    self.assertEqual(len(queue), 0)

                finally:
                    for process in started:
                        if process.is_alive():
                            process.terminate()
                        process.join()
                        process.close()


if __name__ == "__main__":
    unittest.main()