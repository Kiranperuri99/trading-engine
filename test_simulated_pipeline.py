import tempfile
import unittest
from pathlib import Path

from market_simulator import generate_orders
from ring_buffer import RingBuffer
from trading_engine import ChronosMatch


class TestSimulatedPipeline(unittest.TestCase):

    def test_ring_pipeline_matches_direct_engine(self):
        direct = ChronosMatch(verbose=False)
        queued = ChronosMatch(verbose=False)

        # Generate fresh orders for each engine because matching
        # changes an order's remaining quantity.
        for order in generate_orders(100, seed=42):
            direct.add_order(order)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"

            with RingBuffer(path, 4) as ring:
                for order in generate_orders(100, seed=42):
                    ring.put(order)

                    if len(ring) == ring.capacity:
                        while len(ring):
                            queued.add_order(ring.get())

                while len(ring):
                    queued.add_order(ring.get())

                self.assertEqual(len(ring), 0)

        self.assertEqual(queued.trades, direct.trades)
        self.assertEqual(queued.buy_orders, direct.buy_orders)
        self.assertEqual(queued.sell_orders, direct.sell_orders)

    def test_matching_preserves_total_quantity(self):
        engine = ChronosMatch(verbose=False)
        submitted_quantity = 0

        for order in generate_orders(100, seed=42):
            submitted_quantity += order.quantity
            engine.add_order(order)

        pending = engine.pending_quantities()
        matched = engine.total_traded_quantity()

        self.assertEqual(
            submitted_quantity,
            pending["BUY"] + pending["SELL"] + 2 * matched,
        )


if __name__ == "__main__":
    unittest.main()