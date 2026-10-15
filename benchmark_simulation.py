from time import perf_counter_ns

from run_simulation import run_simulation


def benchmark_simulation(count=1000, seed=42):
    start = perf_counter_ns()
    summary = run_simulation(count=count, seed=seed)
    elapsed_ns = perf_counter_ns() - start

    processed = summary["orders_processed"]
    elapsed_seconds = elapsed_ns / 1_000_000_000

    return {
        "orders_processed": processed,
        "elapsed_ns": elapsed_ns,
        "orders_per_second": (
            processed / elapsed_seconds if elapsed_seconds > 0 else None
        ),
        "average_ns_per_order": (
            elapsed_ns / processed if processed > 0 else None
        ),
    }


if __name__ == "__main__":
    result = benchmark_simulation()

    print("ChronosMatch sequential baseline")
    print("Includes generation, file setup, queueing, matching, and cleanup.")

    for name, value in result.items():
        print(f"{name}: {value}")