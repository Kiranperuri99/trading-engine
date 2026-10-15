from ring_layout import HEADER_STRUCT, validate_header
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

    def test_validate_header_accepts_valid_queue_states(self):
        for header in (
            (3, 0, 0, 0),
            (3, 0, 2, 2),
            (3, 2, 1, 2),
            (3, 1, 1, 3),
        ):
            with self.subTest(header=header):
                buffer = bytearray(storage_size(3))
                HEADER_STRUCT.pack_into(buffer, 0, *header)

                self.assertEqual(validate_header(buffer), header)

    def test_validate_header_rejects_invalid_queue_states(self):
        for header in (
            (0, 0, 0, 0),
            (3, 3, 0, 0),
            (3, 0, 3, 0),
            (3, 0, 0, 4),
            (3, 0, 2, 1),
        ):
            with self.subTest(header=header):
                buffer = bytearray(storage_size(3))
                HEADER_STRUCT.pack_into(buffer, 0, *header)

                with self.assertRaises(ValueError):
                    validate_header(buffer)

    def test_validate_header_rejects_wrong_buffer_size(self):
        with self.assertRaises(ValueError):
            validate_header(bytearray(HEADER_SIZE - 1))

        buffer = bytearray(storage_size(3) + 1)
        HEADER_STRUCT.pack_into(buffer, 0, 3, 0, 0, 0)

        with self.assertRaises(ValueError):
            validate_header(buffer)
if __name__ == "__main__":
    unittest.main()