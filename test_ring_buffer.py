from mapped_storage import MappedStorage
from order_codec import decode_order_from
from ring_layout import slot_offset
from trading_engine import Order
import tempfile
import unittest
from pathlib import Path

from ring_buffer import RingBuffer
from ring_layout import HEADER_STRUCT, storage_size


class TestRingBuffer(unittest.TestCase):

    def test_new_ring_is_empty_with_requested_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"

            with RingBuffer(path, 3) as ring:
                self.assertEqual(ring.capacity, 3)
                self.assertEqual(len(ring), 0)

            self.assertEqual(path.stat().st_size, storage_size(3))
            self.assertEqual(
                HEADER_STRUCT.unpack_from(path.read_bytes()),
                (3, 0, 0, 0),
            )

    def test_invalid_capacity_creates_no_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"

            for capacity in (0, -1, True, 2.5, 1 << 64):
                with self.subTest(capacity=capacity):
                    with self.assertRaises(ValueError):
                        RingBuffer(path, capacity)

                    self.assertFalse(path.exists())

    def test_put_stores_order_and_updates_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            order = Order(1, "BUY", 100.0, 5)

            with RingBuffer(path, 2) as ring:
                ring.put(order)
                self.assertEqual(len(ring), 1)

                with MappedStorage.open_existing(path) as view:
                    self.assertEqual(
                        HEADER_STRUCT.unpack_from(view.buffer),
                        (2, 0, 1, 1),
                    )
                    self.assertEqual(
                        decode_order_from(view.buffer, slot_offset(0, 2)),
                        order,
                    )

    def test_full_ring_preserves_existing_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            original = Order(1, "BUY", 100.0, 5)

            with RingBuffer(path, 1) as ring:
                ring.put(original)

                with self.assertRaises(BufferError):
                    ring.put(Order(2, "SELL", 101.0, 3))

                self.assertEqual(len(ring), 1)

                with MappedStorage.open_existing(path) as view:
                    self.assertEqual(
                        decode_order_from(view.buffer, slot_offset(0, 1)),
                        original,
                    )
    def test_invalid_order_leaves_ring_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"

            with RingBuffer(path, 2) as ring:
                with self.assertRaises(ValueError):
                    ring.put(Order(1, "BUY", 100.0, 0))

                self.assertEqual(len(ring), 0)
if __name__ == "__main__":
    unittest.main()