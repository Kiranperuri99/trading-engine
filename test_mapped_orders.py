from order_codec import encode_order_into
from order_codec import decode_order_from
import tempfile
import unittest
from pathlib import Path

from mapped_storage import MappedStorage
from order_codec import ORDER_SIZE, encode_order
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

                    restored = decode_order_from(reader.buffer)

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
                    restored = decode_order_from(storage.buffer, start)
                    self.assertEqual(restored, expected)
    def test_direct_read_sees_updated_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"

            with MappedStorage(path, ORDER_SIZE) as writer:
                with MappedStorage.open_existing(path) as reader:
                    original = Order(1, "BUY", 100.0, 10)
                    writer.buffer[:] = encode_order(original)
                    writer.buffer.flush()

                    first_read = decode_order_from(reader.buffer)
                    self.assertEqual(first_read, original)

                    updated = Order(1, "BUY", 100.0, 4)
                    writer.buffer[:] = encode_order(updated)
                    writer.buffer.flush()

                    second_read = decode_order_from(reader.buffer)
                    self.assertEqual(second_read, updated)
                    self.assertEqual(first_read.quantity, 10)
    def test_direct_write_and_read_between_mappings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"
            first = Order(1, "BUY", 99.0, 10)
            second = Order(2, "SELL", 102.0, 5)

            with MappedStorage(path, ORDER_SIZE * 2) as writer:
                with MappedStorage.open_existing(path) as reader:
                    encode_order_into(first, writer.buffer)
                    encode_order_into(second, writer.buffer, ORDER_SIZE)
                    writer.buffer.flush()

                    self.assertEqual(
                        decode_order_from(reader.buffer),
                        first,
                    )
                    self.assertEqual(
                        decode_order_from(reader.buffer, ORDER_SIZE),
                        second,
                    )

                    updated = Order(1, "BUY", 99.0, 4)
                    encode_order_into(updated, writer.buffer)
                    writer.buffer.flush()

                    self.assertEqual(
                        decode_order_from(reader.buffer),
                        updated,
                    )
                    self.assertEqual(
                        decode_order_from(reader.buffer, ORDER_SIZE),
                        second,
                    )
if __name__ == "__main__":
    unittest.main()