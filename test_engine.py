import unittest
from importlib.machinery import SourceFileLoader

engine_module = SourceFileLoader(
    "trading_engine",
    "trading-engine-main.py"
).load_module()

Order = engine_module.Order
ChronosMatch = engine_module.ChronosMatch


class TestChronosMatch(unittest.TestCase):

    def test_matching_orders(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 101.0, 10))
        engine.add_order(Order(2, "SELL", 100.0, 5))

        self.assertEqual(len(engine.buy_orders), 1)
        self.assertEqual(engine.buy_orders[0].quantity, 5)
        self.assertEqual(len(engine.sell_orders), 0)

    def test_orders_do_not_match(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 99.0, 10))
        engine.add_order(Order(2, "SELL", 100.0, 5))

        self.assertEqual(len(engine.buy_orders), 1)
        self.assertEqual(len(engine.sell_orders), 1)

    def test_rejects_non_positive_quantity(self):
        for quantity in (0, -5):
            with self.subTest(quantity=quantity):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, "BUY", 100.0, quantity))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
    def test_rejects_invalid_price(self):
        for price in (0, -10, float("nan"), float("inf"), float("-inf")):
            with self.subTest(price=price):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, "BUY", price, 5))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
    def test_rejects_non_integer_quantity(self):
        for quantity in (2.5, "5", True, None):
            with self.subTest(quantity=quantity):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, "BUY", 100.0, quantity))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
    def test_rejects_invalid_order_id(self):
        for order_id in (0, -1, 1.5, "1", True, None):
            with self.subTest(order_id=order_id):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(order_id, "BUY", 100.0, 5))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, []) 
    def test_accepts_side_with_spaces_and_lowercase(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, " buy ", 100.0, 5))
        engine.add_order(Order(2, " sell ", 100.0, 5))

        self.assertEqual(engine.buy_orders, [])
        self.assertEqual(engine.sell_orders, [])

    def test_rejects_invalid_side(self):
        for side in ("HOLD", "", "   ", None, 123):
            with self.subTest(side=side):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, side, 100.0, 5))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])           
if __name__ == "__main__":
    unittest.main()