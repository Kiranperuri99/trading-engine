"""Live terminal graph for ChronosMatch engine-call latency."""

import argparse
import sys
from collections import deque

from latency_stats import summarize_latencies
from measure_engine_latency import measure_engine_latency
from result_export import save_result
from run_simulation import non_negative_count


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Value must be a positive integer") from error
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer")
    return number


def render_frame(
    samples,
    completed,
    total,
    side,
    width=80,
    samples_by_side=None,
    p99_budget_ns=None,
    side_p99_budgets=None,
):
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

    if p99_budget_ns is not None:
        p99_ns = stats["p99_ns"]
        if p99_ns is None:
            budget_status = "waiting for samples"
        elif p99_ns <= p99_budget_ns:
            budget_status = f"within budget (p99 {p99_ns} ns)"
        else:
            budget_status = f"OVER BUDGET (p99 {p99_ns} ns)"
        lines.insert(
            4,
            f"P99 budget: {p99_budget_ns} ns | {budget_status}",
        )

    if samples_by_side is not None:
        side_summaries = []
        for side_name in ("BUY", "SELL"):
            side_stats = summarize_latencies(samples_by_side.get(side_name, ()))
            side_budget_ns = (side_p99_budgets or {}).get(
                side_name, p99_budget_ns
            )
            side_summary = (
                f"{side_name} median {show(side_stats['median_ns'])} ns, "
                f"p99 {show(side_stats['p99_ns'])} ns"
            )
            if side_budget_ns is not None:
                side_p99 = side_stats["p99_ns"]
                if side_p99 is None:
                    side_status = "waiting for samples"
                elif side_p99 <= side_budget_ns:
                    side_status = "within budget"
                else:
                    side_status = "OVER BUDGET"
                side_summary += f" | budget {side_status}"
            side_summaries.append(
                side_summary
            )
        lines.insert(4, " | ".join(side_summaries))

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
    report_path=None,
    p99_budget_ns=None,
    buy_p99_budget_ns=None,
    sell_p99_budget_ns=None,
):
    if type(window) is not int or window <= 0:
        raise ValueError("Window size must be a positive integer")
    if type(refresh_every) is not int or refresh_every <= 0:
        raise ValueError("Refresh interval must be a positive integer")
    if p99_budget_ns is not None and (
        type(p99_budget_ns) is not int or p99_budget_ns <= 0
    ):
        raise ValueError("P99 budget must be a positive integer")
    for side_name, side_budget in (
        ("BUY", buy_p99_budget_ns),
        ("SELL", sell_p99_budget_ns),
    ):
        if side_budget is not None and (
            type(side_budget) is not int or side_budget <= 0
        ):
            raise ValueError(f"{side_name} p99 budget must be a positive integer")

    side_p99_budgets = {
        "BUY": buy_p99_budget_ns if buy_p99_budget_ns is not None else p99_budget_ns,
        "SELL": sell_p99_budget_ns if sell_p99_budget_ns is not None else p99_budget_ns,
    }

    output = sys.stdout if output is None else output
    history = deque(maxlen=window)
    history_by_side = {
        "BUY": deque(maxlen=window),
        "SELL": deque(maxlen=window),
    }

    def draw(completed, total, side):
        output.write("\033[2J\033[H")
        output.write(
            render_frame(
                history,
                completed,
                total,
                side,
                samples_by_side=history_by_side,
                p99_budget_ns=p99_budget_ns,
                side_p99_budgets=side_p99_budgets,
            )
        )
        output.write("\n")
        output.flush()

    def on_sample(elapsed_ns, completed, total, side):
        history.append(elapsed_ns)
        history_by_side[side].append(elapsed_ns)
        if completed % refresh_every == 0 or completed == total:
            draw(completed, total, side)

    measurement_options = {
        "count": count,
        "seed": seed,
        "warmup": warmup,
        "on_sample": on_sample,
    }
    if report_path is not None:
        measurement_options["include_samples"] = True

    result = measure_engine_latency(**measurement_options)
    if count == 0:
        draw(0, 0, None)
    if p99_budget_ns is not None:
        p99_ns = result["latency"]["p99_ns"]
        result["p99_budget"] = {
            "limit_ns": p99_budget_ns,
            "measured_ns": p99_ns,
            "within_budget": None if p99_ns is None else p99_ns <= p99_budget_ns,
        }
    configured_side_budgets = {
        side_name: budget
        for side_name, budget in side_p99_budgets.items()
        if budget is not None
    }
    if configured_side_budgets:
        result["p99_budget_by_side"] = {}
        for side_name, side_budget in configured_side_budgets.items():
            side_p99 = result.get("latency_by_side", {}).get(side_name, {}).get(
                "p99_ns"
            )
            result["p99_budget_by_side"][side_name] = {
                "limit_ns": side_budget,
                "measured_ns": side_p99,
                "within_budget": (
                    None if side_p99 is None else side_p99 <= side_budget
                ),
            }
    if report_path is not None:
        save_result(report_path, result)
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
    parser.add_argument(
        "--p99-budget-ns",
        type=positive_integer,
        help="Show whether the rolling p99 latency stays within this nanosecond budget",
    )
    parser.add_argument(
        "--buy-p99-budget-ns",
        type=positive_integer,
        help="Override the p99 latency budget for BUY orders",
    )
    parser.add_argument(
        "--sell-p99-budget-ns",
        type=positive_integer,
        help="Override the p99 latency budget for SELL orders",
    )
    parser.add_argument(
        "--fail-on-budget-exceeded",
        action="store_true",
        help="Exit with status 1 if the p99 budget is exceeded or no samples are measured",
    )
    parser.add_argument(
        "--output",
        help="Save the final JSON report, including measured samples, to a new file",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.fail_on_budget_exceeded and not any((
        args.p99_budget_ns,
        args.buy_p99_budget_ns,
        args.sell_p99_budget_ns,
    )):
        parser.error("--fail-on-budget-exceeded requires at least one p99 budget")

    result = run_live_dashboard(
        count=args.count,
        seed=args.seed,
        warmup=args.warmup,
        window=args.window,
        refresh_every=args.refresh_every,
        report_path=args.output,
        p99_budget_ns=args.p99_budget_ns,
        buy_p99_budget_ns=args.buy_p99_budget_ns,
        sell_p99_budget_ns=args.sell_p99_budget_ns,
    )
    budget_results = []
    if "p99_budget" in result:
        budget_results.append(result["p99_budget"]["within_budget"])
    budget_results.extend(
        side_result["within_budget"]
        for side_result in result.get("p99_budget_by_side", {}).values()
    )
    if args.fail_on_budget_exceeded and any(
        status is not True for status in budget_results
    ):
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    main()
