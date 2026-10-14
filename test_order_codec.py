
from order_codec import decode_order
from order_codec import encode_order
from trading_engine import Order
import unittest

from order_codec import BUY, SELL, ORDER_SIZE, ORDER_STRUCT

class TestOrderCodec(unittest.TestCase):

    def test_order_record_is_25_bytes(self):
        self.assertEqual(ORDER_SIZE, 25)

    def test_binary_layout_preserves_fields(self):
        for side in (BUY, SELL):
            with self.subTest(side=side):
                record = ORDER_STRUCT.pack(42, side, 101.5, 10)

                self.assertEqual(len(record), ORDER_SIZE)
                self.assertEqual(
                    ORDER_STRUCT.unpack(record),
                    (42, side, 101.5, 10),
                )

    def test_encode_order_preserves_fields(self):
        for side, code in ((" buy ", BUY), ("SELL", SELL)):
            with self.subTest(side=side):
                order = Order(42, side, 101.5, 10)

                record = encode_order(order)

                self.assertEqual(len(record), 25)
                self.assertEqual(
                    ORDER_STRUCT.unpack(record),
                    (42, code, 101.5, 10),
                )
                self.assertEqual(order.side, side)

    def test_encode_rejects_values_outside_binary_range(self):
        orders = [
            Order(1 << 64, "BUY", 100.0, 5),
            Order(1, "BUY", 100.0, 1 << 64),
            Order(0, "BUY", 100.0, 5),
            Order(1, "BUY", 100.0, -1),
        ]

        for order in orders:
            with self.subTest(order=order):
                with self.assertRaises(ValueError):
                    encode_order(order)
    def test_encode_decode_round_trip(self):
        for side in ("BUY", "SELL"):
            with self.subTest(side=side):
                original = Order(42, side, 101.5, 10)

                restored = decode_order(encode_order(original))

                self.assertEqual(restored, original)

    def test_decode_rejects_wrong_record_size(self):
        for record in (b"", bytes(24), bytes(26)):
            with self.subTest(size=len(record)):
                with self.assertRaises(ValueError):
                    decode_order(record)

    def test_decode_rejects_invalid_fields(self):
        fields = [
            (1, 3, 100.0, 5),
            (0, BUY, 100.0, 5),
            (1, BUY, 100.0, 0),
            (1, BUY, -1.0, 5),
            (1, BUY, float("nan"), 5),
            (1, BUY, float("inf"), 5),
        ]

        for values in fields:
            with self.subTest(values=values):
                record = ORDER_STRUCT.pack(*values)

                with self.assertRaises(ValueError):
                    decode_order(record)
    def test_largest_integer_fields_survive_round_trip(self):
        maximum = (1 << 64) - 1
        original = Order(maximum, "SELL", 100.0, maximum)

        restored = decode_order(encode_order(original))

        self.assertEqual(restored, original)

    def test_encode_rejects_invalid_field_types(self):
        orders = [
            Order(True, "BUY", 100.0, 5),
            Order("1", "BUY", 100.0, 5),
            Order(1, "BUY", 100.0, True),
            Order(1, "BUY", 100.0, 2.5),
            Order(1, "BUY", "100", 5),
            Order(1, "BUY", True, 5),
            Order(1, None, 100.0, 5),
            Order(1, "HOLD", 100.0, 5),
        ]

        for order in orders:
            with self.subTest(order=order):
                with self.assertRaises(ValueError):
                    encode_order(order)
if __name__ == "__main__":
    unittest.main()