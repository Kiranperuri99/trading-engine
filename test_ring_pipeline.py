import tempfile
import unittest
from pathlib import Path

from ring_buffer import RingBuffer
from trading_engine import ChronosMatch, Order


class TestRingPipeline(unittest.TestCase):

    def test_queued_orders_produce_trade_and_partial_fill(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            engine = ChronosMatch(verbose=False)

            with RingBuffer(path, 2) as ring:
                ring.put(Order(1, "BUY", 101.0, 10))
                ring.put(Order(2, "SELL", 100.0, 5))

                while len(ring):
                    engine.add_order(ring.get())

                self.assertEqual(len(ring), 0)

            self.assertEqual(engine.trades, [{
                "buy_order_id": 1,
                "sell_order_id": 2,
                "price": 101.0,
                "quantity": 5,
            }])
            self.assertEqual(
                engine.pending_quantities(),
                {"BUY": 5, "SELL": 0},
            )

    def test_reused_ring_slot_delivers_another_trade(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            engine = ChronosMatch(verbose=False)

            with RingBuffer(path, 1) as ring:
                for order in (
                    Order(1, "BUY", 100.0, 10),
                    Order(2, "SELL", 100.0, 4),
                    Order(3, "SELL", 100.0, 6),
                ):
                    ring.put(order)
                    engine.add_order(ring.get())

                self.assertEqual(len(ring), 0)

            self.assertEqual(len(engine.trades), 2)
            self.assertEqual(engine.total_traded_quantity(), 10)
            self.assertEqual(
                engine.pending_quantities(),
                {"BUY": 0, "SELL": 0},
            )

    def test_queued_non_crossing_orders_remain_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            engine = ChronosMatch(verbose=False)

            with RingBuffer(path, 2) as ring:
                ring.put(Order(1, "BUY", 99.0, 4))
                ring.put(Order(2, "SELL", 100.0, 3))

                while len(ring):
                    engine.add_order(ring.get())

                self.assertEqual(len(ring), 0)

            self.assertEqual(engine.trades, [])
            self.assertEqual(
                engine.pending_quantities(),
                {"BUY": 4, "SELL": 3},
            )
if __name__ == "__main__":
    unittest.main()