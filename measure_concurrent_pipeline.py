import argparse
import json
from time import perf_counter_ns

from run_concurrent import (
    positive_capacity,
    positive_timeout,
    run_concurrent,
)
from run_simulation import non_negative_count


def measure_concurrent_pipeline(count=1000, seed=42, capacity=16, timeout=30):
    started_ns = perf_counter_ns()
    summary = run_concurrent(
        count=count,
        seed=seed,
        capacity=capacity,
        timeout=timeout,
    )
    elapsed_ns = perf_counter_ns() - started_ns
    processed = summary["orders_processed"]

    orders_per_second = (
        processed * 1_000_000_000 / elapsed_ns if elapsed_ns else 0.0
    )

    return {
        "scope": "Concurrent run including worker startup",
        "configuration": {
            "count": count,
            "seed": seed,
            "capacity": capacity,
            "timeout": timeout,
        },
        "elapsed_ns": elapsed_ns,
        "orders_per_second": round(orders_per_second, 2),
        "summary": summary,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure ChronosMatch concurrent pipeline throughput."
    )
    parser.add_argument("--count", type=non_negative_count, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--capacity", type=positive_capacity, default=16)
    parser.add_argument("--timeout", type=positive_timeout, default=30.0)
    args = parser.parse_args(argv)

    result = measure_concurrent_pipeline(
        count=args.count,
        seed=args.seed,
        capacity=args.capacity,
        timeout=args.timeout,
    )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
    