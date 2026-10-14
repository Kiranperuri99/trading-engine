import multiprocessing
import tempfile
import unittest
from pathlib import Path

from mapped_storage import MappedStorage
from order_codec import ORDER_SIZE, decode_order_from, encode_order_into
from trading_engine import Order


def verify_order_in_child(path):
    with MappedStorage.open_existing(path) as storage:
        restored = decode_order_from(storage.buffer)
        expected = Order(42, "BUY", 101.5, 10)

        if restored != expected:
            raise AssertionError(
                f"Expected {expected}, received {restored}"
            )


class TestMappedProcess(unittest.TestCase):

    def test_separate_process_reads_mapped_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.bin"

            with MappedStorage(path, ORDER_SIZE) as storage:
                encode_order_into(
                    Order(42, "BUY", 101.5, 10),
                    storage.buffer,
                )
                storage.buffer.flush()

                context = multiprocessing.get_context("spawn")
                process = context.Process(
                    target=verify_order_in_child,
                    args=(str(path),),
                )

                process.start()

                try:
                    process.join(timeout=15)

                    self.assertFalse(
                        process.is_alive(),
                        "Child process did not finish within 15 seconds",
                    )
                    self.assertEqual(
                        process.exitcode,
                        0,
                        "Child process failed to read the expected order",
                    )
                finally:
                    if process.is_alive():
                        process.terminate()
                        process.join()

                    process.close()


if __name__ == "__main__":
    unittest.main()