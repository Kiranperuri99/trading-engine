import multiprocessing
import tempfile
import unittest
from pathlib import Path

from ring_buffer import RingBuffer
from run_simulation import run_simulation
from simulation_workers import produce_orders, consume_orders
from synchronized_ring import SynchronizedRing


class TestWorkerPipeline(unittest.TestCase):

    def test_workers_match_sequential_simulation(self):
        count = 20
        seed = 7
        expected = run_simulation(count=count, seed=seed)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()

            with RingBuffer(path, count) as ring:
                queue = SynchronizedRing(ring, lock)

                produced = produce_orders(
                    queue, count, seed=seed, timeout=10
                )
                result = consume_orders(queue, count, timeout=10)

                self.assertEqual(produced, count)
                self.assertEqual(result, expected)
                self.assertEqual(len(queue), 0)

    def test_workers_can_reuse_drained_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            lock = multiprocessing.get_context("spawn").Lock()

            with RingBuffer(path, 3) as ring:
                queue = SynchronizedRing(ring, lock)

                for seed in (7, 42):
                    produced = produce_orders(
                        queue, 2, seed=seed, timeout=10
                    )
                    result = consume_orders(queue, 2, timeout=10)

                    self.assertEqual(produced, 2)
                    self.assertEqual(
                        result,
                        run_simulation(count=2, seed=seed),
                    )
                    self.assertEqual(len(queue), 0)


if __name__ == "__main__":
    unittest.main()