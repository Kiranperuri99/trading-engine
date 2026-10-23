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
    def test_existing_mapping_preserves_saved_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"

            with MappedStorage(path, 100) as storage:
                storage.buffer[:4] = b"TEST"
                storage.buffer.flush()

            with MappedStorage.open_existing(path) as storage:
                self.assertEqual(len(storage.buffer), 100)
                self.assertEqual(storage.buffer[:4], b"TEST")

    def test_two_mappings_share_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"

            with MappedStorage(path, 100) as first:
                with MappedStorage.open_existing(path) as second:
                    first.buffer[:4] = b"BUY!"
                    first.buffer.flush()
                    self.assertEqual(second.buffer[:4], b"BUY!")

                    second.buffer[4:8] = b"SELL"
                    second.buffer.flush()
                    self.assertEqual(first.buffer[4:8], b"SELL")
    def test_context_manager_persists_data_on_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"

            with MappedStorage(path, 100) as storage:
                storage.buffer[:4] = b"EXIT"

            self.assertEqual(path.read_bytes()[:4], b"EXIT")
    def test_open_existing_missing_file_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.bin"

            with self.assertRaises(FileNotFoundError):
                MappedStorage.open_existing(path)

            self.assertFalse(path.exists())
if __name__ == "__main__":
    unittest.main()