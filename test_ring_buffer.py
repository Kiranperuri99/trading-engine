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


if __name__ == "__main__":
    unittest.main()