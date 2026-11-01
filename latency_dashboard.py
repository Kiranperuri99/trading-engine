"""Live terminal graph for ChronosMatch engine-call latency."""

import argparse
import csv
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from latency_stats import histogram_latencies, summarize_latencies
from measure_engine_latency import measure_engine_latency, summarize_throughput
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


def save_samples_csv(path, samples):
    with Path(path).open("x", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(
            ("order_number", "order_id", "side", "latency_ns", "recorded_at_utc")
        )
        writer.writerows(samples)


def render_frame(
    samples,
    completed,
    total,
    side,
    width=80,
    samples_by_side=None,
    p99_budget_ns=None,
    side_p99_budgets=None,
    p99_9_budget_ns=None,
    side_p99_9_budgets=None,
):
    values = list(samples)
    stats = summarize_latencies(values)
    max_value = max(values, default=0)
    graph_width = max(width - 24, 1)

    def show(value):
        return "n/a" if value is None else f"{value}"

    def show_rate(sample_values):
        rate = summarize_throughput(sample_values)["orders_per_second"]
        return "n/a" if rate is None else f"{rate:,.1f}"

    lines = [
        "ChronosMatch live engine-call latency (nanoseconds)",
        "Scope: one add_order call; excludes order generation and queue wait.",
        f"Progress: {completed}/{total} | Last side: {side or '-'} | Window: {len(values)}",
        (
            f"min {show(stats['min_ns'])} | median {show(stats['median_ns'])} | "
            f"p95 {show(stats['p95_ns'])} | p99 {show(stats['p99_ns'])} | "
            f"p99.9 {show(stats['p99_9_ns'])}"
        ),
        "Recent samples (newest at bottom):",
    ]

    if p99_budget_ns is not None:
        p99_ns = stats["p99_ns"]
        if p99_ns is None:
            budget_status = "waiting for samples"
        elif p99_ns <= p99_budget_ns:
            utilization = round(p99_ns / p99_budget_ns * 100, 1)
            budget_status = (
                f"within budget (p99 {p99_ns} ns) | {utilization:.1f}% used"
            )
        else:
            utilization = round(p99_ns / p99_budget_ns * 100, 1)
            budget_status = (
                f"OVER BUDGET (p99 {p99_ns} ns) | {utilization:.1f}% used"
            )
        lines.insert(
            4,
            f"P99 budget: {p99_budget_ns} ns | {budget_status}",
        )

    if p99_9_budget_ns is not None:
        p99_9_ns = stats["p99_9_ns"]
        if p99_9_ns is None:
            budget_status = "waiting for samples"
        elif p99_9_ns <= p99_9_budget_ns:
            utilization = round(p99_9_ns / p99_9_budget_ns * 100, 1)
            budget_status = (
                f"within budget (p99.9 {p99_9_ns} ns) | {utilization:.1f}% used"
            )
        else:
            utilization = round(p99_9_ns / p99_9_budget_ns * 100, 1)
            budget_status = (
                f"OVER BUDGET (p99.9 {p99_9_ns} ns) | {utilization:.1f}% used"
            )
        lines.insert(4, f"P99.9 budget: {p99_9_budget_ns} ns | {budget_status}")

    if samples_by_side is not None:
        side_summaries = []
        for side_name in ("BUY", "SELL"):
            side_samples = samples_by_side.get(side_name, ())
            side_stats = summarize_latencies(side_samples)
            side_budget_ns = (side_p99_budgets or {}).get(
                side_name, p99_budget_ns
            )
            side_summary = (
                f"{side_name} median {show(side_stats['median_ns'])} ns, "
                f"p95 {show(side_stats['p95_ns'])} ns, "
                f"p99 {show(side_stats['p99_ns'])} ns, "
                f"p99.9 {show(side_stats['p99_9_ns'])} ns"
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
                if side_p99 is not None:
                    utilization = round(side_p99 / side_budget_ns * 100, 1)
                    side_summary += f" ({utilization:.1f}% used)"
            side_p99_9_budget_ns = (side_p99_9_budgets or {}).get(
                side_name, p99_9_budget_ns
            )
            if side_p99_9_budget_ns is not None:
                side_p99_9 = side_stats["p99_9_ns"]
                if side_p99_9 is None:
                    side_p99_9_status = "waiting for samples"
                elif side_p99_9 <= side_p99_9_budget_ns:
                    side_p99_9_status = "within budget"
                else:
                    side_p99_9_status = "OVER BUDGET"
                side_summary += f" | p99.9 budget {side_p99_9_status}"
                if side_p99_9 is not None:
                    utilization = round(
                        side_p99_9 / side_p99_9_budget_ns * 100, 1
                    )
                    side_summary += f" ({utilization:.1f}% used)"
            side_summary += (
                f" | aggregate call rate {show_rate(side_samples)} orders/s"
            )
            side_summaries.append(
                side_summary
            )
        lines.insert(4, " | ".join(side_summaries))

    sample_header_index = lines.index("Recent samples (newest at bottom):")
    lines.insert(
        sample_header_index,
        f"Aggregate engine-call rate (sum of timed calls): "
        f"{show_rate(values)} orders/s",
    )

    for value in values:
        bar_size = (
            max(1, round(value / max_value * graph_width))
            if max_value > 0 and value > 0
            else 0
        )
        lines.append(f"{value:>10} ns | {'#' * bar_size}")

    if not values:
        lines.append("Waiting for the first measurement...")

    histogram = histogram_latencies(values)
    side_histograms = (
        {
            side_name: histogram_latencies(samples_by_side.get(side_name, ()))
            for side_name in ("BUY", "SELL")
        }
        if samples_by_side is not None
        else None
    )
    histogram_lines = ["Latency histogram by nanosecond range:"]
    for bucket, count in histogram.items():
        histogram_line = f"  {bucket} ns | window {count}"
        if side_histograms is not None:
            histogram_line += (
                f" | BUY window {side_histograms['BUY'][bucket]}"
                f" | SELL window {side_histograms['SELL'][bucket]}"
            )
        histogram_lines.append(histogram_line)
    sample_header_index = lines.index("Recent samples (newest at bottom):")
    lines[sample_header_index:sample_header_index] = histogram_lines

    return "\n".join(lines)


def run_live_dashboard(
    count=1000,
    seed=42,
    warmup=0,
    window=30,
    refresh_every=10,
    output=None,
    report_path=None,
    csv_path=None,
    p99_budget_ns=None,
    buy_p99_budget_ns=None,
    sell_p99_budget_ns=None,
    p99_9_budget_ns=None,
    buy_p99_9_budget_ns=None,
    sell_p99_9_budget_ns=None,
):
    if type(window) is not int or window <= 0:
        raise ValueError("Window size must be a positive integer")
    if type(refresh_every) is not int or refresh_every <= 0:
        raise ValueError("Refresh interval must be a positive integer")
    if p99_budget_ns is not None and (
        type(p99_budget_ns) is not int or p99_budget_ns <= 0
    ):
        raise ValueError("P99 budget must be a positive integer")
    if p99_9_budget_ns is not None and (
        type(p99_9_budget_ns) is not int or p99_9_budget_ns <= 0
    ):
        raise ValueError("P99.9 budget must be a positive integer")
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
    side_p99_9_budgets = {
        "BUY": buy_p99_9_budget_ns if buy_p99_9_budget_ns is not None else p99_9_budget_ns,
        "SELL": sell_p99_9_budget_ns if sell_p99_9_budget_ns is not None else p99_9_budget_ns,
    }

    for side_name, side_budget in (
        ("BUY", buy_p99_9_budget_ns),
        ("SELL", sell_p99_9_budget_ns),
    ):
        if side_budget is not None and (
            type(side_budget) is not int or side_budget <= 0
        ):
            raise ValueError(
                f"{side_name} p99.9 budget must be a positive integer"
            )

    output = sys.stdout if output is None else output
    history = deque(maxlen=window)
    history_by_side = {
        "BUY": deque(maxlen=window),
        "SELL": deque(maxlen=window),
    }
    csv_samples = []

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
                p99_9_budget_ns=p99_9_budget_ns,
                side_p99_9_budgets=side_p99_9_budgets,
            )
        )
        output.write("\n")
        output.flush()

    def on_sample(elapsed_ns, completed, total, side):
        history.append(elapsed_ns)
        history_by_side[side].append(elapsed_ns)
        if completed % refresh_every == 0 or completed == total:
            draw(completed, total, side)

    def on_order_sample(elapsed_ns, completed, total, side, order_id):
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
        "count": count,
        "seed": seed,
        "warmup": warmup,
        "on_sample": on_sample,
    }
    if report_path is not None:
        measurement_options["include_samples"] = True
    if csv_path is not None:
        measurement_options["on_order_sample"] = on_order_sample

    result = measure_engine_latency(**measurement_options)
    if count == 0:
        draw(0, 0, None)
    if p99_budget_ns is not None:
        p99_ns = result["latency"]["p99_ns"]
        result["p99_budget"] = _budget_result(p99_ns, p99_budget_ns)
    if p99_9_budget_ns is not None:
        p99_9 = result["latency"]["p99_9_ns"]
        result["p99_9_budget"] = _budget_result(p99_9, p99_9_budget_ns)
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
            result["p99_budget_by_side"][side_name] = _budget_result(
                side_p99, side_budget
            )
    configured_side_p99_9_budgets = {
        side_name: budget
        for side_name, budget in side_p99_9_budgets.items()
        if budget is not None
    }
    if configured_side_p99_9_budgets:
        result["p99_9_budget_by_side"] = {}
        for side_name, side_budget in configured_side_p99_9_budgets.items():
            side_p99_9 = result.get("latency_by_side", {}).get(
                side_name, {}
            ).get("p99_9_ns")
            result["p99_9_budget_by_side"][side_name] = _budget_result(
                side_p99_9, side_budget
            )
    result["dashboard"] = {
        "window": window,
        "refresh_every": refresh_every,
    }
    if report_path is not None:
        save_result(report_path, result)
    if csv_path is not None:
        save_samples_csv(csv_path, csv_samples)
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
        "--p99-9-budget-ns",
        type=positive_integer,
        help="Show whether the rolling p99.9 latency stays within this nanosecond budget",
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
        "--buy-p99-9-budget-ns",
        type=positive_integer,
        help="Override the p99.9 latency budget for BUY orders",
    )
    parser.add_argument(
        "--sell-p99-9-budget-ns",
        type=positive_integer,
        help="Override the p99.9 latency budget for SELL orders",
    )
    parser.add_argument(
        "--fail-on-budget-exceeded",
        action="store_true",
        help=(
            "Exit with status 1 if any configured p99 or p99.9 budget is exceeded "
            "or unavailable"
        ),
    )
    parser.add_argument(
        "--output",
        help="Save the final JSON report, including measured samples, to a new file",
    )
    parser.add_argument(
        "--csv-output",
        help="Save each measured order latency as a CSV row in a new file",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.fail_on_budget_exceeded and not any((
        args.p99_budget_ns,
        args.buy_p99_budget_ns,
        args.sell_p99_budget_ns,
        args.p99_9_budget_ns,
        args.buy_p99_9_budget_ns,
        args.sell_p99_9_budget_ns,
    )):
        parser.error(
            "--fail-on-budget-exceeded requires at least one p99 or p99.9 budget"
        )

    result = run_live_dashboard(
        count=args.count,
        seed=args.seed,
        warmup=args.warmup,
        window=args.window,
        refresh_every=args.refresh_every,
        report_path=args.output,
        csv_path=args.csv_output,
        p99_budget_ns=args.p99_budget_ns,
        buy_p99_budget_ns=args.buy_p99_budget_ns,
        sell_p99_budget_ns=args.sell_p99_budget_ns,
        p99_9_budget_ns=args.p99_9_budget_ns,
        buy_p99_9_budget_ns=args.buy_p99_9_budget_ns,
        sell_p99_9_budget_ns=args.sell_p99_9_budget_ns,
    )
    budget_results = []
    if "p99_budget" in result:
        budget_results.append(result["p99_budget"]["within_budget"])
    budget_results.extend(
        side_result["within_budget"]
        for side_result in result.get("p99_budget_by_side", {}).values()
    )
    if "p99_9_budget" in result:
        budget_results.append(result["p99_9_budget"]["within_budget"])
    budget_results.extend(
        side_result["within_budget"]
        for side_result in result.get("p99_9_budget_by_side", {}).values()
    )
    if args.fail_on_budget_exceeded and any(
        status is not True for status in budget_results
    ):
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    main()
