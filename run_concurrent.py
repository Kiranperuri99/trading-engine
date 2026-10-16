import json
import multiprocessing
import tempfile
from pathlib import Path
from time import monotonic, sleep

from process_workers import producer_process, consumer_process
from ring_buffer import RingBuffer
from worker_config import validate_timeout


def run_concurrent(count=100, seed=42, capacity=16, timeout=30):
    if type(count) is not int or not 0 <= count <= (1 << 64) - 1:
        raise ValueError("Count must be a non-negative 64-bit integer")

    timeout = validate_timeout(timeout)
    context = multiprocessing.get_context("spawn")
    lock = context.Lock()

    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        path = directory / "ring.bin"
        producer_result = directory / "producer.json"
        consumer_result = directory / "consumer.json"

        with RingBuffer(path, capacity):
            pass

        processes = [
            context.Process(
                name="producer",
                target=producer_process,
                args=(
                    str(path), lock, count, seed,
                    timeout, str(producer_result),
                ),
            ),
            context.Process(
                name="consumer",
                target=consumer_process,
                args=(
                    str(path), lock, count,
                    timeout, str(consumer_result),
                ),
            ),
        ]
        started = []
        deadline = monotonic() + timeout

        try:
            for process in processes:
                process.start()
                started.append(process)

            while True:
                for process in started:
                    if process.exitcode not in (None, 0):
                        raise RuntimeError(
                            f"{process.name} failed with exit code "
                            f"{process.exitcode}"
                        )

                if all(process.exitcode == 0 for process in started):
                    break

                if monotonic() >= deadline:
                    raise TimeoutError("Concurrent simulation timed out")

                sleep(0.01)

            producer = json.loads(
                producer_result.read_text(encoding="utf-8")
            )
            summary = json.loads(
                consumer_result.read_text(encoding="utf-8")
            )

            if producer["orders_produced"] != count:
                raise RuntimeError("Producer order count is incorrect")

            if summary["orders_processed"] != count:
                raise RuntimeError("Consumer order count is incorrect")

            return summary

        finally:
            for process in started:
                if process.is_alive():
                    process.terminate()

            for process in started:
                process.join()
                process.close()


if __name__ == "__main__":
    result = run_concurrent()
    print("ChronosMatch concurrent simulation")

    for name, value in result.items():
        print(f"{name}: {value}")
        