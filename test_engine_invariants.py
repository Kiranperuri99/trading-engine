import random
import unittest
from trading_engine import ChronosMatch, Order


class TestEngineInvariants(unittest.TestCase):
    def test_seeded_order_flow_preserves_invariants(self):
        rng = random.Random(42)
        engine = ChronosMatch(verbose=False)
        submitted = {"BUY": 0, "SELL": 0}

        for order_id in range(1, 201):
            side = rng.choice(("BUY", "SELL"))
            price = float(rng.randint(90, 110))
            quantity = rng.randint(1, 10)
            submitted[side] += quantity
            engine.add_order(Order(order_id, side, price, quantity))

            with self.subTest(order_id=order_id):
                traded = engine.total_traded_quantity()
                pending = engine.pending_quantities()

                for book_side in ("BUY", "SELL"):
                    self.assertEqual(
                        submitted[book_side],
                        traded + pending[book_side],
                    )

                bid = engine.best_bid()
                ask = engine.best_ask()
                if bid is not None and ask is not None:
                    self.assertLess(bid, ask)

                for order in engine.buy_orders + engine.sell_orders:
                    self.assertGreater(order.quantity, 0)


if __name__ == "__main__":
    unittest.main()