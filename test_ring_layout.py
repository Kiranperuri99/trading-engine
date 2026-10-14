import unittest

from order_codec import ORDER_SIZE
from ring_layout import HEADER_SIZE, slot_offset, storage_size


class TestRingLayout(unittest.TestCase):

    def test_storage_size_includes_header_and_slots(self):
        self.assertEqual(HEADER_SIZE, 32)
        self.assertEqual(storage_size(3), 32 + 3 * ORDER_SIZE)

    def test_slots_are_adjacent_and_fit_storage(self):
        self.assertEqual(slot_offset(0, 3), HEADER_SIZE)
        self.assertEqual(
            slot_offset(1, 3) - slot_offset(0, 3),
            ORDER_SIZE,
        )
        self.assertEqual(
            slot_offset(2, 3) + ORDER_SIZE,
            storage_size(3),
        )

    def test_invalid_capacity_is_rejected(self):
        for capacity in (0, -1, True, 2.5):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    storage_size(capacity)

    def test_invalid_slot_is_rejected(self):
        for index in (-1, 3, True, 1.5):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    slot_offset(index, 3)


if __name__ == "__main__":
    unittest.main()