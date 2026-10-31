import csv
from datetime import datetime, timezone
from unittest import result
from unittest import result
from result_export import save_result
from benchmark_environment import benchmark_environment
import json
import argparse
from pathlib import Path
from run_simulation import non_negative_count
from time import perf_counter_ns

from engine_summary import summarize_engine
from latency_stats import histogram_latencies, summarize_latencies
from market_simulator import generate_orders
from trading_engine import ChronosMatch


def summarize_throughput(samples):
    measured_call_time_ns = sum(samples)
    orders_per_second = (
        len(samples) * 1_000_000_000 / measured_call_time_ns
        if measured_call_time_ns > 0
        else None
    )
    return {
        "measured_call_time_ns": measured_call_time_ns,
        "orders_per_second": orders_per_second,
    }


def save_samples_csv(path, samples):
    with Path(path).open("x", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(
            ("order_number", "order_id", "side", "latency_ns", "recorded_at_utc")
        )
        writer.writerows(samples)


def measure_engine_latency(
    count=1000,
    seed=42,
    warmup=0,
    include_samples=False,
    on_sample=None,
    on_order_sample=None,
):
    engine = ChronosMatch(verbose=False)
    samples = []
    side_samples = {"BUY": [], "SELL": []}

    if warmup:
        warmup_engine = ChronosMatch(verbose=False)
        for warmup_order in generate_orders(warmup, seed + 1):
            warmup_engine.add_order(warmup_order)

    for completed, order in enumerate(generate_orders(count, seed), start=1):
        start = perf_counter_ns()
        engine.add_order(order)
        elapsed = perf_counter_ns() - start

        samples.append(elapsed)
        side = order.side.strip().upper()
        side_samples[side].append(elapsed)
        if on_sample is not None:
            on_sample(elapsed, completed, count, side)
        if on_order_sample is not None:
            on_order_sample(elapsed, completed, count, side, order.order_id)

    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": benchmark_environment(),
        "scope": "ChronosMatch.add_order call",
        "configuration": {
            "count": count,
            "seed": seed,
            "warmup": warmup,
        },
        "latency": summarize_latencies(samples),
        "latency_by_side": {
            side: summarize_latencies(side_samples[side])
            for side in ("BUY", "SELL")
        },
        "latency_histogram": histogram_latencies(samples),
        "latency_histogram_by_side": {
            side: histogram_latencies(side_samples[side])
            for side in ("BUY", "SELL")
        },
        "throughput": summarize_throughput(samples),
        "throughput_by_side": {
            side: summarize_throughput(side_samples[side])
            for side in ("BUY", "SELL")
        },
        "summary": summarize_engine(engine, len(samples)),
    }

    if include_samples:
        result["samples_ns"] = samples

    return result


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Value must be a positive integer"
        ) from error
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer")
    return number


def _budget_result(measured_ns, limit_ns):
    return {
        "limit_ns": limit_ns,
        "measured_ns": measured_ns,
        "within_budget": (
            None if measured_ns is None else measured_ns <= limit_ns
        ),
        "utilization_percent": (
            None if measured_ns is None else round(measured_ns / limit_ns * 100, 1)
        ),
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
    parser.add_argument(
        "--warmup",
        type=non_negative_count,
        default=0,
        help="Process this many orders before measuring",
    )
    parser.add_argument(
        "--include-samples",
        action="store_true",
        help="Include each order's latency in the report",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        help="Save one row per measured order to a new CSV file",
    )
    parser.add_argument(
        "--p95-budget-ns",
        type=positive_integer,
        help="Set a maximum p95 engine-call latency in nanoseconds",
    )
    parser.add_argument(
        "--p99-budget-ns",
        type=positive_integer,
        help="Set a maximum p99 engine-call latency in nanoseconds",
    )
    parser.add_argument(
        "--fail-on-budget-exceeded",
        action="store_true",
        help="Exit with status 1 when a configured latency budget is missed or unavailable",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.output and args.csv_output is not None:
        json_path = Path(args.output).resolve()
        csv_path = args.csv_output.resolve()
        if json_path == csv_path:
            parser.error("--output and --csv-output must use different file paths")
    if args.fail_on_budget_exceeded and not any((
        args.p95_budget_ns,
        args.p99_budget_ns,
    )):
        parser.error("--fail-on-budget-exceeded requires a p95 or p99 budget")

    csv_samples = []

    def record_order_sample(elapsed_ns, completed, total, side, order_id):
        csv_samples.append(
            (
                completed,
                order_id,
                side,
                elapsed_ns,
                datetime.now(timezone.utc).isoformat(),
            )
        )

    measurement_options = {
        "count": args.count,
        "seed": args.seed,
        "warmup": args.warmup,
        "include_samples": args.include_samples,
    }
    if args.csv_output is not None:
        measurement_options["on_order_sample"] = record_order_sample

    result = measure_engine_latency(**measurement_options)
    budget_statuses = []
    for percentile in ("p95", "p99"):
        limit_ns = getattr(args, f"{percentile}_budget_ns")
        if limit_ns is None:
            continue
        budget = _budget_result(result["latency"][f"{percentile}_ns"], limit_ns)
        result[f"{percentile}_budget"] = budget
        budget_statuses.append(budget["within_budget"])

    if args.output:
        save_result(args.output, result)
    if args.csv_output is not None:
        save_samples_csv(args.csv_output, csv_samples)

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

        if "latency_histogram" in result:
            print("Latency histogram (sample count by nanosecond range):")
            for bucket, count in result["latency_histogram"].items():
                print(f"  {bucket}: {count}")

        if "throughput" in result:
            print("Engine-call throughput (sum of timed add_order calls):")
            for name, value in result["throughput"].items():
                print(f"  {name}: {value}")
            for side, stats in result.get("throughput_by_side", {}).items():
                print(f"{side} order throughput:")
                for name, value in stats.items():
                    print(f"  {name}: {value}")

        for percentile in ("p95", "p99"):
            budget = result.get(f"{percentile}_budget")
            if budget is None:
                continue
            measured_ns = budget["measured_ns"]
            if measured_ns is None:
                status = "waiting for samples"
            elif budget["within_budget"]:
                status = f"within budget | {budget['utilization_percent']:.1f}% used"
            else:
                status = f"OVER BUDGET | {budget['utilization_percent']:.1f}% used"
            measured_text = "n/a" if measured_ns is None else str(measured_ns)
            print(
                f"{percentile.upper()} budget: {budget['limit_ns']} ns | "
                f"measured {measured_text} ns | {status}"
            )

        if result.get("summary"):
            print("Engine summary:")
            for name, value in result["summary"].items():
                print(f" {name}: {value}")
        

    if args.fail_on_budget_exceeded and any(
        status is not True for status in budget_statuses
    ):
        raise SystemExit(1)

    return result
    

if __name__ == "__main__":
    main()
