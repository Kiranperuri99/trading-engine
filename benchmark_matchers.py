"""Compare the Python and Cython matching cores on identical order streams."""

import argparse
import json
from statistics import median
from time import perf_counter_ns

from benchmark_environment import benchmark_environment
from market_simulator import generate_orders
from run_simulation import non_negative_count
from trading_engine import ChronosMatch, Order

try:
    from cython_matcher import CythonMatchCore
except ImportError:
    CythonMatchCore = None


def positive_count(value):
    count = non_negative_count(value)
    if count == 0:
        raise argparse.ArgumentTypeError("Order count must be greater than zero")
    return count


def positive_repeats(value):
    try:
        repeats = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Repeat count must be a positive whole number"
        ) from None
    if repeats <= 0:
        raise argparse.ArgumentTypeError(
            "Repeat count must be a positive whole number"
        )
    return repeats


def non_negative_warmup(value):
    try:
        warmup = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Warm-up count must be a non-negative whole number"
        ) from None
    if warmup < 0:
        raise argparse.ArgumentTypeError(
            "Warm-up count must be a non-negative whole number"
        )
    return warmup


def _copy_orders(orders):
    return [
        Order(order.order_id, order.side, order.price, order.quantity)
        for order in orders
    ]


def _engine_snapshot(engine):
    def orders_in(book):
        return [
            (order.order_id, order.side, order.price, order.quantity)
            for order in book
        ]

    return {
        "trades": engine.trades,
        "buy_orders": orders_in(engine.buy_orders),
        "sell_orders": orders_in(engine.sell_orders),
        "pending_quantities": engine.pending_quantities(),
        "total_traded_quantity": engine.total_traded_quantity(),
    }


def _run_once(engine_factory, order_templates):
    engine = engine_factory(verbose=False)
    orders = _copy_orders(order_templates)

    start_ns = perf_counter_ns()
    for order in orders:
        engine.add_order(order)
    elapsed_ns = perf_counter_ns() - start_ns

    return elapsed_ns, _engine_snapshot(engine)


def _summarize(samples_ns, count, snapshot):
    median_elapsed_ns = median(samples_ns)
    return {
        "samples_ns": samples_ns,
        "median_elapsed_ns": median_elapsed_ns,
        "orders_per_second": (
            count * 1_000_000_000 / median_elapsed_ns
            if median_elapsed_ns > 0
            else None
        ),
        "median_ns_per_order": median_elapsed_ns / count,
        "trade_count": len(snapshot["trades"]),
        "traded_quantity": snapshot["total_traded_quantity"],
        "pending_quantities": snapshot["pending_quantities"],
    }


def benchmark_matchers(count=1000, seed=42, repeats=5, warmup=1):
    """Benchmark add_order with generation and engine setup outside timing."""
    if type(count) is not int or count <= 0:
        raise ValueError("Order count must be a positive integer")
    if type(repeats) is not int or repeats <= 0:
        raise ValueError("Repeat count must be a positive integer")
    if type(warmup) is not int or warmup < 0:
        raise ValueError("Warm-up count must be a non-negative integer")
    if CythonMatchCore is None:
        raise RuntimeError(
            "Cython matcher is unavailable; build it with "
            "python setup_cython.py build_ext --inplace"
        )

    order_templates = list(generate_orders(count, seed))
    factories = {
        "python": ChronosMatch,
        "cython": CythonMatchCore,
    }
    samples = {name: [] for name in factories}
    last_snapshots = {}

    def run_pair(reverse=False, measured=False):
        names = list(factories)
        if reverse:
            names.reverse()
        pair_snapshots = {}
        for name in names:
            elapsed_ns, snapshot = _run_once(
                factories[name],
                order_templates,
            )
            pair_snapshots[name] = snapshot
            if measured:
                samples[name].append(elapsed_ns)
        if pair_snapshots["python"] != pair_snapshots["cython"]:
            raise RuntimeError(
                "Python and Cython matcher results differ for the benchmark workload"
            )
        return pair_snapshots

    for index in range(warmup):
        last_snapshots = run_pair(reverse=bool(index % 2))

    for index in range(repeats):
        last_snapshots = run_pair(
            reverse=bool((index + warmup) % 2),
            measured=True,
        )

    results = {
        name: _summarize(samples[name], count, last_snapshots[name])
        for name in factories
    }
    python_median = results["python"]["median_elapsed_ns"]
    cython_median = results["cython"]["median_elapsed_ns"]

    return {
        "configuration": {
            "mode": "matching-core",
            "count": count,
            "seed": seed,
            "repeats": repeats,
            "warmup": warmup,
        },
        "environment": benchmark_environment(),
        "results": results,
        "cython_speedup_ratio": (
            python_median / cython_median if cython_median > 0 else None
        ),
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Compare Python and Cython order-matching throughput."
    )
    parser.add_argument(
        "--count",
        type=positive_count,
        default=1000,
        help="Orders in each run (default: 1000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for the repeatable order stream (default: 42)",
    )
    parser.add_argument(
        "--repeats",
        type=positive_repeats,
        default=5,
        help="Measured runs per matcher (default: 5)",
    )
    parser.add_argument(
        "--warmup",
        type=non_negative_warmup,
        default=1,
        help="Unmeasured runs per matcher (default: 1)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the benchmark report as JSON",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = benchmark_matchers(
            count=args.count,
            seed=args.seed,
            repeats=args.repeats,
            warmup=args.warmup,
        )
    except RuntimeError as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(result, indent=2, allow_nan=False))
        return

    print("ChronosMatch Python vs Cython matcher benchmark")
    print(
        f"Orders: {args.count}; seed: {args.seed}; "
        f"warm-up: {args.warmup}; repeats: {args.repeats}"
    )
    print("Timing covers add_order calls, not order generation or engine setup.")
    for name, values in result["results"].items():
        print(f"{name}: median_ns={values['median_elapsed_ns']}")
        print(f"{name}: orders_per_second={values['orders_per_second']}")
        print(f"{name}: median_ns_per_order={values['median_ns_per_order']}")
    print(f"cython_speedup_ratio: {result['cython_speedup_ratio']}")


if __name__ == "__main__":
    main()
