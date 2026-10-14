import tempfile
import unittest
from pathlib import Path

from mapped_storage import MappedStorage
from order_codec import ORDER_SIZE, encode_order, decode_order
from trading_engine import Order


class TestMappedOrders(unittest.TestCase):

    def test_order_can_be_read_from_second_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"
            original = Order(1, "BUY", 101.5, 10)

            with MappedStorage(path, ORDER_SIZE) as writer:
                with MappedStorage.open_existing(path) as reader:
                    writer.buffer[:ORDER_SIZE] = encode_order(original)
                    writer.buffer.flush()

                    restored = decode_order(reader.buffer[:ORDER_SIZE])

                    self.assertEqual(restored, original)

    def test_adjacent_order_records_remain_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"
            orders = [
                Order(1, "BUY", 99.0, 10),
                Order(2, "SELL", 102.0, 5),
            ]

            with MappedStorage(path, ORDER_SIZE * 2) as storage:
                for index, order in enumerate(orders):
                    start = index * ORDER_SIZE
                    storage.buffer[start:start + ORDER_SIZE] = (
                        encode_order(order)
                    )

                storage.buffer.flush()

            with MappedStorage.open_existing(path) as storage:
                for index, expected in enumerate(orders):
                    start = index * ORDER_SIZE
                    restored = decode_order(
                        storage.buffer[start:start + ORDER_SIZE]
                    )
                    self.assertEqual(restored, expected)


if __name__ == "__main__":
    unittest.main()