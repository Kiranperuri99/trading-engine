from benchmark_environment import benchmark_environment
import argparse
from run_simulation import non_negative_count
from time import perf_counter_ns

from run_simulation import run_simulation


def benchmark_simulation(count=1000, seed=42):
    start = perf_counter_ns()
    summary = run_simulation(count=count, seed=seed)
    elapsed_ns = perf_counter_ns() - start

    processed = summary["orders_processed"]
    elapsed_seconds = elapsed_ns / 1_000_000_000

    return {
         "configuration": {
            "mode": "sequential",
            "count": count,
            "seed": seed,
            "capacity": 16,
        },
        "environment": benchmark_environment(),
        "orders_processed": processed,
        "elapsed_ns": elapsed_ns,
        "orders_per_second": (
            processed / elapsed_seconds if elapsed_seconds > 0 else None
        ),
        "average_ns_per_order": (
            elapsed_ns / processed if processed > 0 else None
        ),
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Measure the whole sequential simulation."
    )
    parser.add_argument(
        "--count",
        type=non_negative_count,
        default=1000,
        help="Number of simulated orders (default: 1000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = benchmark_simulation(count=args.count, seed=args.seed)

    print("ChronosMatch sequential baseline")
    print(f"Requested orders: {args.count}; seed: {args.seed}")
    print("Includes generation, file setup, queueing, matching, and cleanup.")

    for name, value in result.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()