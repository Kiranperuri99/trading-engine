from benchmark_environment import benchmark_environment
from time import perf_counter_ns

from run_concurrent import run_concurrent


def benchmark_concurrent(
    count=1000, seed=42, capacity=16, timeout=30
):
    start = perf_counter_ns()
    summary = run_concurrent(
        count=count,
        seed=seed,
        capacity=capacity,
        timeout=timeout,
    )
    elapsed_ns = perf_counter_ns() - start
    processed = summary["orders_processed"]

    return {
        "environment": benchmark_environment(),
        "orders_processed": processed,
        "elapsed_ns": elapsed_ns,
        "orders_per_second": (
            processed * 1_000_000_000 / elapsed_ns
            if elapsed_ns > 0 else None
        ),
        "average_ns_per_order": (
            elapsed_ns / processed if processed > 0 else None
        ),
    }


if __name__ == "__main__":
    result = benchmark_concurrent()

    print("ChronosMatch concurrent baseline")
    print("Includes setup, process startup, processing, and cleanup.")

    for name, value in result.items():
        print(f"{name}: {value}")
