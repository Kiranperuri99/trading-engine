import random
import unittest

from trading_engine import ChronosMatch, Order

try:
    from cython_matcher import CythonMatchCore
except ImportError:
    CythonMatchCore = None


@unittest.skipIf(
    CythonMatchCore is None,
    "Build the Cython extension with setup_cython.py before running this test",
)
class TestCythonMatchCore(unittest.TestCase):
    def assert_engines_match(self, python_engine, cython_engine):
        self.assertEqual(python_engine.trades, cython_engine.trades)
        self.assertEqual(
            [(order.order_id, order.side, order.price, order.quantity)
             for order in python_engine.buy_orders],
            [(order.order_id, order.side, order.price, order.quantity)
             for order in cython_engine.buy_orders],
        )
        self.assertEqual(
            [(order.order_id, order.side, order.price, order.quantity)
             for order in python_engine.sell_orders],
            [(order.order_id, order.side, order.price, order.quantity)
             for order in cython_engine.sell_orders],
        )
        self.assertEqual(
            python_engine.pending_quantities(),
            cython_engine.pending_quantities(),
        )
        self.assertEqual(
            python_engine.total_traded_quantity(),
            cython_engine.total_traded_quantity(),
        )

    def submit_to_both(self, python_engine, cython_engine, order):
        python_engine.add_order(
            Order(order.order_id, order.side, order.price, order.quantity)
        )
        cython_engine.add_order(
            Order(order.order_id, order.side, order.price, order.quantity)
        )
        self.assert_engines_match(python_engine, cython_engine)

    def test_fifo_partial_fills_match_python_engine(self):
        python_engine = ChronosMatch(verbose=False)
        cython_engine = CythonMatchCore(verbose=False)

        for order in (
            Order(20, "BUY", 100.0, 3),
            Order(10, "BUY", 100.0, 4),
            Order(30, "SELL", 100.0, 5),
        ):
            self.submit_to_both(python_engine, cython_engine, order)

        self.assertEqual(
            [trade["buy_order_id"] for trade in cython_engine.trades],
            [20, 10],
        )
        self.assertEqual(cython_engine.buy_orders[0].quantity, 2)

    def test_each_incoming_side_uses_resting_order_price(self):
        cases = (
            (
                (Order(1, "SELL", 100, 2), Order(2, "BUY", 105, 2)),
                100,
            ),
            (
                (Order(1, "BUY", 105, 2), Order(2, "SELL", 100, 2)),
                105,
            ),
        )
        for orders, expected_price in cases:
            with self.subTest(expected_price=expected_price):
                python_engine = ChronosMatch(verbose=False)
                cython_engine = CythonMatchCore(verbose=False)
                for order in orders:
                    self.submit_to_both(python_engine, cython_engine, order)
                self.assertEqual(cython_engine.trades[0]["price"], expected_price)

    def test_deterministic_order_stream_matches_python_engine(self):
        randomizer = random.Random(19)
        python_engine = ChronosMatch(verbose=False)
        cython_engine = CythonMatchCore(verbose=False)

        for order_id in range(1, 501):
            order = Order(
                order_id,
                randomizer.choice(("BUY", "SELL")),
                float(randomizer.randrange(95, 106)),
                randomizer.randrange(1, 9),
            )
            self.submit_to_both(python_engine, cython_engine, order)

    def test_invalid_and_duplicate_orders_are_rejected(self):
        engine = CythonMatchCore(verbose=False)

        invalid_orders = (
            None,
            Order(0, "BUY", 100.0, 1),
            Order(1, "BUY", 100.0, 0),
            Order(2, "BID", 100.0, 1),
        )
        for order in invalid_orders:
            with self.subTest(order=order):
                with self.assertRaises((TypeError, ValueError)):
                    engine.add_order(order)

        engine.add_order(Order(3, "BUY", 100.0, 1))
        with self.assertRaisesRegex(ValueError, "already been used"):
            engine.add_order(Order(3, "SELL", 100.0, 1))

    def test_cancel_order_matches_python_engine_for_both_sides(self):
        python_engine = ChronosMatch(verbose=False)
        cython_engine = CythonMatchCore(verbose=False)
        for order in (
            Order(1, "BUY", 100.0, 2),
            Order(2, "BUY", 99.0, 3),
            Order(3, "SELL", 101.0, 4),
            Order(4, "SELL", 102.0, 5),
        ):
            self.submit_to_both(python_engine, cython_engine, order)

        for order_id in (2, 3):
            with self.subTest(order_id=order_id):
                self.assertEqual(
                    cython_engine.cancel_order(order_id),
                    python_engine.cancel_order(order_id),
                )
                self.assert_engines_match(python_engine, cython_engine)

        self.assertEqual(
            [order.order_id for order in cython_engine.buy_orders],
            [1],
        )
        self.assertEqual(
            [order.order_id for order in cython_engine.sell_orders],
            [4],
        )
        self.assertFalse(cython_engine.cancel_order(2))
        with self.assertRaisesRegex(ValueError, "positive whole number"):
            cython_engine.cancel_order(0)

        with self.assertRaisesRegex(ValueError, "already been used"):
            cython_engine.add_order(Order(2, "BUY", 98.0, 1))

    def test_order_status_matches_python_engine_lifecycle(self):
        python_engine = ChronosMatch(verbose=False)
        cython_engine = CythonMatchCore(verbose=False)

        for order_id in (99, 2**64):
            self.assertEqual(
                cython_engine.get_order_status(order_id),
                python_engine.get_order_status(order_id),
            )

        self.submit_to_both(
            python_engine,
            cython_engine,
            Order(1, "BUY", 100.0, 3),
        )
        self.assertEqual(cython_engine.get_order_status(1), "OPEN")

        self.submit_to_both(
            python_engine,
            cython_engine,
            Order(2, "SELL", 100.0, 3),
        )
        for order_id in (1, 2):
            self.assertEqual(
                cython_engine.get_order_status(order_id),
                python_engine.get_order_status(order_id),
            )
            self.assertEqual(cython_engine.get_order_status(order_id), "FILLED")

        self.submit_to_both(
            python_engine,
            cython_engine,
            Order(3, "BUY", 99.0, 2),
        )
        self.assertTrue(python_engine.cancel_order(3))
        self.assertTrue(cython_engine.cancel_order(3))
        self.assertEqual(cython_engine.get_order_status(3), "CANCELLED")

        for invalid_id in (0, -1, True, 1.5, "1", None):
            with self.subTest(order_id=invalid_id):
                with self.assertRaises(ValueError):
                    cython_engine.get_order_status(invalid_id)


if __name__ == "__main__":
    unittest.main()
