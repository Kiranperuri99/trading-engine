"""Live terminal graph for ChronosMatch engine-call latency."""

import argparse
import sys
from collections import deque

from latency_stats import summarize_latencies
from measure_engine_latency import measure_engine_latency
from run_simulation import non_negative_count


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Value must be a positive integer") from error
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer")
    return number


def render_frame(samples, completed, total, side, width=80):
    values = list(samples)
    stats = summarize_latencies(values)
    max_value = max(values, default=0)
    graph_width = max(width - 24, 1)

    def show(value):
        return "n/a" if value is None else f"{value}"

    lines = [
        "ChronosMatch live engine-call latency (nanoseconds)",
        "Scope: one add_order call; excludes order generation and queue wait.",
        f"Progress: {completed}/{total} | Last side: {side or '-'} | Window: {len(values)}",
        (
            f"min {show(stats['min_ns'])} | median {show(stats['median_ns'])} | "
            f"p95 {show(stats['p95_ns'])} | p99 {show(stats['p99_ns'])}"
        ),
        "Recent samples (newest at bottom):",
    ]

    for value in values:
        bar_size = (
            max(1, round(value / max_value * graph_width))
            if max_value > 0 and value > 0
            else 0
        )
        lines.append(f"{value:>10} ns | {'#' * bar_size}")

    if not values:
        lines.append("Waiting for the first measurement...")

    return "\n".join(lines)


def run_live_dashboard(
    count=1000,
    seed=42,
    warmup=0,
    window=30,
    refresh_every=10,
    output=None,
):
    if type(window) is not int or window <= 0:
        raise ValueError("Window size must be a positive integer")
    if type(refresh_every) is not int or refresh_every <= 0:
        raise ValueError("Refresh interval must be a positive integer")

    output = sys.stdout if output is None else output
    history = deque(maxlen=window)

    def draw(completed, total, side):
        output.write("\033[2J\033[H")
        output.write(render_frame(history, completed, total, side))
        output.write("\n")
        output.flush()

    def on_sample(elapsed_ns, completed, total, side):
        history.append(elapsed_ns)
        if completed % refresh_every == 0 or completed == total:
            draw(completed, total, side)

    result = measure_engine_latency(
        count=count,
        seed=seed,
        warmup=warmup,
        on_sample=on_sample,
    )
    if count == 0:
        draw(0, 0, None)
    return result


def build_parser():
    parser = argparse.ArgumentParser(
        description="Display a live graph of matching-engine call latency."
    )
    parser.add_argument("--count", type=non_negative_count, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--warmup", type=non_negative_count, default=100)
    parser.add_argument(
        "--window",
        type=positive_integer,
        default=30,
        help="Number of recent samples to graph (default: 30)",
    )
    parser.add_argument(
        "--refresh-every",
        type=positive_integer,
        default=10,
        help="Redraw after this many new orders (default: 10)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return run_live_dashboard(
        count=args.count,
        seed=args.seed,
        warmup=args.warmup,
        window=args.window,
        refresh_every=args.refresh_every,
    )


if __name__ == "__main__":
    main()
