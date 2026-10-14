import unittest

from order_codec import decode_order, encode_order
from trading_engine import ChronosMatch, Order


class TestBinaryPipeline(unittest.TestCase):

    def test_binary_orders_produce_trade_and_partial_fill(self):
        engine = ChronosMatch(verbose=False)

        orders = [
            Order(1, "BUY", 101.0, 10),
            Order(2, "SELL", 100.0, 5),
        ]

        for order in orders:
            record = encode_order(order)
            restored_order = decode_order(record)
            engine.add_order(restored_order)

        self.assertEqual(engine.trades, [{
            "buy_order_id": 1,
            "sell_order_id": 2,
            "price": 100.0,
            "quantity": 5,
        }])
        self.assertEqual(
            engine.pending_quantities(),
            {"BUY": 5, "SELL": 0},
        )

        # Matching restored orders must not change the originals.
        self.assertEqual(orders[0].quantity, 10)
        self.assertEqual(orders[1].quantity, 5)

    def test_binary_orders_with_non_crossing_prices_wait(self):
        engine = ChronosMatch(verbose=False)

        for order in (
            Order(1, "BUY", 99.0, 4),
            Order(2, "SELL", 102.0, 6),
        ):
            engine.add_order(decode_order(encode_order(order)))

        self.assertEqual(engine.trades, [])
        self.assertEqual(engine.spread(), 3.0)
        self.assertEqual(
            engine.pending_quantities(),
            {"BUY": 4, "SELL": 6},
        )


if __name__ == "__main__":
    unittest.main()