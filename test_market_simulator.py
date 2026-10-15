import unittest

from market_simulator import generate_orders
from order_codec import encode_order, decode_order


class TestMarketSimulator(unittest.TestCase):

    def test_same_seed_produces_same_orders(self):
        first = list(generate_orders(20, seed=42))
        second = list(generate_orders(20, seed=42))

        self.assertEqual(first, second)

    def test_generated_orders_have_unique_ids_and_valid_fields(self):
        orders = list(generate_orders(100, seed=42))

        self.assertEqual(
            [order.order_id for order in orders],
            list(range(1, 101)),
        )

        for order in orders:
            self.assertIn(order.side, ("BUY", "SELL"))
            self.assertGreaterEqual(order.price, 99.0)
            self.assertLessEqual(order.price, 101.0)
            self.assertGreaterEqual(order.quantity, 1)
            self.assertLessEqual(order.quantity, 10)
            self.assertEqual(
                decode_order(encode_order(order)),
                order,
            )

    def test_zero_count_produces_no_orders(self):
        self.assertEqual(list(generate_orders(0)), [])

    def test_invalid_count_is_rejected(self):
        for count in (-1, True, 2.5, "10", 1 << 64):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    list(generate_orders(count))


if __name__ == "__main__":
    unittest.main()