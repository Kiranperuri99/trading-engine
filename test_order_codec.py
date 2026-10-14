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


if __name__ == "__main__":
    unittest.main()