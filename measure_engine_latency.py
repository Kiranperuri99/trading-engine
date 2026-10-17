from datetime import datetime, timezone
from result_export import save_result
from benchmark_environment import benchmark_environment
import json
import argparse
from run_simulation import non_negative_count
from time import perf_counter_ns

from engine_summary import summarize_engine
from latency_stats import summarize_latencies
from market_simulator import generate_orders
from trading_engine import ChronosMatch


def measure_engine_latency(count=1000, seed=42):
    engine = ChronosMatch(verbose=False)
    samples = []
    side_samples = {"BUY": [], "SELL": []
                    }

    for order in generate_orders(count, seed):
        start = perf_counter_ns()
        engine.add_order(order)
        elapsed = perf_counter_ns() - start
        samples.append(elapsed)
        side = order.side.strip().upper()
        side_samples[side].append(elapsed)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "environment": benchmark_environment(),
        "scope": "ChronosMatch.add_order call",
        "configuration": {
            "count": count,
            "seed": seed,
        },
        "latency": summarize_latencies(samples),
        "latency_by_side": {
    side: summarize_latencies(side_samples[side])
    for side in ("BUY", "SELL")
},
        "summary": summarize_engine(engine, len(samples)),
    }

   


def build_parser():
    parser = argparse.ArgumentParser(
        description="Measure individual matching-engine calls."
    )
    parser.add_argument(
        "--count",
        type=non_negative_count,
        default=1000,
        help="Number of orders to measure (default: 1000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete measurement result as JSON",
    )
    parser.add_argument(
        "--output",
        help="Save results to a new JSON file",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = measure_engine_latency(
        count=args.count,
        seed=args.seed,
    )
    if args.output:
        save_result(args.output, result)

    if args.json:
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        print("ChronosMatch engine-call latency")
        print("Excludes queue waiting and order generation.")
        print(f"Requested orders: {args.count}; seed: {args.seed}")

        for name, value in result["latency"].items():
            print(f"{name}: {value}")

        for side, stats in result.get("latency_by_side", {}).items():
            print(f"{side} order latency:")
            for name, value in stats.items():
                print(f"  {name}: {value}")

        if result.get("summary"):
            print("Engine summary:")
            for name, value in result["summary"].items():
                print(f"  {name}: {value}")
    return result

if __name__ == "__main__":
    main()