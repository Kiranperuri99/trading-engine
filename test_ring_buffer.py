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

                valid_order = Order(2, "SELL", 101.0, 3)
                ring.put(valid_order)

                self.assertEqual(len(ring), 1)
                self.assertEqual(ring.get(), valid_order)
                self.assertEqual(len(ring), 0)
    def test_get_returns_orders_in_arrival_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            first = Order(20, "BUY", 100.0, 5)
            second = Order(10, "SELL", 101.0, 3)

            with RingBuffer(path, 2) as ring:
                ring.put(first)
                ring.put(second)

                self.assertEqual(ring.get(), first)
                self.assertEqual(len(ring), 1)
                self.assertEqual(ring.get(), second)
                self.assertEqual(len(ring), 0)

    def test_get_from_empty_ring_raises_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"

            with RingBuffer(path, 2) as ring:
                with self.assertRaises(BufferError):
                    ring.get()

                self.assertEqual(len(ring), 0)

                order = Order(1, "BUY", 100.0, 5)
                ring.put(order)
                self.assertEqual(ring.get(), order)

    def test_ring_reuses_freed_slots_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            first = Order(1, "BUY", 99.0, 5)
            second = Order(2, "SELL", 102.0, 3)
            third = Order(3, "BUY", 100.0, 4)

            with RingBuffer(path, 2) as ring:
                ring.put(first)
                ring.put(second)
                self.assertEqual(ring.get(), first)

                ring.put(third)

                self.assertEqual(len(ring), 2)
                self.assertEqual(ring.get(), second)
                self.assertEqual(ring.get(), third)
                self.assertEqual(len(ring), 0)
    def test_reopen_preserves_waiting_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            first = Order(1, "BUY", 99.0, 5)
            second = Order(2, "SELL", 102.0, 3)

            with RingBuffer(path, 3) as ring:
                ring.put(first)
                ring.put(second)

            with RingBuffer.open_existing(path) as ring:
                self.assertEqual(ring.capacity, 3)
                self.assertEqual(len(ring), 2)
                self.assertEqual(ring.get(), first)
                self.assertEqual(ring.get(), second)
                self.assertEqual(len(ring), 0)

    def test_reopen_rejects_damaged_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"

            with RingBuffer(path, 2):
                pass

            with MappedStorage.open_existing(path) as storage:
                HEADER_STRUCT.pack_into(
                    storage.buffer, 0, 2, 0, 0, 3
                )
                storage.buffer.flush()

            with self.assertRaises(ValueError):
                RingBuffer.open_existing(path)
    def test_reopen_preserves_wrapped_queue_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            first = Order(1, "BUY", 99.0, 5)
            second = Order(2, "SELL", 102.0, 3)
            third = Order(3, "BUY", 100.0, 4)

            with RingBuffer(path, 2) as ring:
                ring.put(first)
                ring.put(second)
                self.assertEqual(ring.get(), first)
                ring.put(third)

            with RingBuffer.open_existing(path) as ring:
                self.assertEqual(len(ring), 2)
                self.assertEqual(ring.get(), second)
                self.assertEqual(ring.get(), third)
                self.assertEqual(len(ring), 0)

    def test_reopened_empty_queue_can_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            first = Order(1, "BUY", 99.0, 5)
            second = Order(2, "SELL", 102.0, 3)

            with RingBuffer(path, 2) as ring:
                ring.put(first)
                self.assertEqual(ring.get(), first)

            with RingBuffer.open_existing(path) as ring:
                self.assertEqual(len(ring), 0)
                ring.put(second)
                self.assertEqual(ring.get(), second)
                self.assertEqual(len(ring), 0)
    def test_open_instance_reads_order_written_by_another_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            order = Order(5, "BUY", 105.0, 2)

            with RingBuffer(path, 2) as writer:
                with RingBuffer.open_existing(path) as reader:
                    writer.put(order)

                    self.assertEqual(len(reader), 1)
                    self.assertEqual(reader.get(), order)
                    self.assertEqual(len(writer), 0)
    def test_capacity_one_can_be_reused_repeatedly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.bin"
            orders = [
                Order(1, "BUY", 99.0, 2),
                Order(2, "SELL", 101.0, 3),
                Order(3, "BUY", 100.0, 4),
            ]

            with RingBuffer(path, 1) as ring:
                for order in orders:
                    ring.put(order)
                    self.assertEqual(len(ring), 1)
                    self.assertEqual(ring.get(), order)
                    self.assertEqual(len(ring), 0)
    def test_reopen_rejects_out_of_range_positions(self):
        for read_pos, write_pos in ((2, 0), (0, 2)):
            with self.subTest(read_pos=read_pos, write_pos=write_pos):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "ring.bin"

                    with RingBuffer(path, 2):
                        pass

                    with MappedStorage.open_existing(path) as storage:
                        HEADER_STRUCT.pack_into(
                            storage.buffer,
                            0,
                            2,
                            read_pos,
                            write_pos,
                            0,
                        )
                        storage.buffer.flush()

                    with self.assertRaises(ValueError):
                        RingBuffer.open_existing(path)
if __name__ == "__main__":
    unittest.main()