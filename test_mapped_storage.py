import tempfile
import unittest
from pathlib import Path

from mapped_storage import MappedStorage


class TestMappedStorage(unittest.TestCase):

    def test_mapped_data_is_saved_to_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"

            with MappedStorage(path, 100) as storage:
                self.assertEqual(len(storage.buffer), 100)
                storage.buffer[0:4] = b"TEST"
                storage.buffer.flush()

            self.assertEqual(path.stat().st_size, 100)
            self.assertEqual(path.read_bytes()[:4], b"TEST")

    def test_existing_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"
            path.write_bytes(b"keep this")

            with self.assertRaises(FileExistsError):
                MappedStorage(path, 100)

            self.assertEqual(path.read_bytes(), b"keep this")

    def test_invalid_size_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"

            for size in (0, -1, True, 2.5):
                with self.subTest(size=size):
                    with self.assertRaises(ValueError):
                        MappedStorage(path, size)

                    self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()