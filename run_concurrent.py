import argparse
from run_simulation import non_negative_count
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
def positive_capacity(value):
    capacity = non_negative_count(value)

    if capacity == 0:
        raise argparse.ArgumentTypeError("Capacity must be positive")

    return capacity


def positive_timeout(value):
    try:
        return validate_timeout(float(value))
    except (ValueError, OverflowError):
        raise argparse.ArgumentTypeError(
            "Timeout must be a positive finite number"
        ) from None


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the concurrent ChronosMatch simulation."
    )
    parser.add_argument("--count", type=non_negative_count, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--capacity", type=positive_capacity, default=16)
    parser.add_argument("--timeout", type=positive_timeout, default=30.0)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the simulation summary as JSON",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = run_concurrent(
        count=args.count,
        seed=args.seed,
        capacity=args.capacity,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        print("ChronosMatch concurrent simulation")

        for name, value in result.items():
            print(f"{name}: {value}")

if __name__ == "__main__":
    main()


