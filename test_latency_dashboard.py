import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from latency_dashboard import (
    build_parser,
    main,
    render_frame,
    run_live_dashboard,
)


class TestLatencyDashboard(unittest.TestCase):
    def test_render_empty_dashboard(self):
        frame = render_frame([], completed=0, total=0, side=None)

        self.assertIn("Progress: 0/0", frame)
        self.assertIn("Waiting for the first measurement", frame)
        self.assertIn("median n/a", frame)

    def test_render_frame_reports_p99_budget_state(self):
        within = render_frame(
            [10, 20], completed=2, total=2, side="BUY", p99_budget_ns=20
        )
        exceeded = render_frame(
            [10, 20], completed=2, total=2, side="BUY", p99_budget_ns=19
        )
        waiting = render_frame(
            [], completed=0, total=0, side=None, p99_budget_ns=20
        )

        self.assertIn("P99 budget: 20 ns | within budget (p99 20 ns)", within)
        self.assertIn("P99 budget: 19 ns | OVER BUDGET (p99 20 ns)", exceeded)
        self.assertIn("P99 budget: 20 ns | waiting for samples", waiting)

    def test_live_dashboard_rejects_non_positive_p99_budget(self):
        for budget in (0, -1, 1.5, True):
            with self.subTest(budget=budget):
                with self.assertRaisesRegex(ValueError, "P99 budget"):
                    run_live_dashboard(p99_budget_ns=budget)

    def test_fail_flag_requires_a_p99_budget(self):
        error_output = io.StringIO()
        with patch("sys.stderr", error_output):
            with self.assertRaises(SystemExit) as raised:
                main(["--fail-on-budget-exceeded"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("requires --p99-budget-ns", error_output.getvalue())

    def test_fail_flag_exits_nonzero_when_budget_is_missed_or_unavailable(self):
        for within_budget in (False, None):
            with self.subTest(within_budget=within_budget):
                with patch(
                    "latency_dashboard.run_live_dashboard",
                    return_value={"p99_budget": {"within_budget": within_budget}},
                ):
                    with self.assertRaises(SystemExit) as raised:
                        main([
                            "--p99-budget-ns", "50000",
                            "--fail-on-budget-exceeded",
                        ])

                self.assertEqual(raised.exception.code, 1)

    def test_fail_flag_returns_normally_when_budget_is_met(self):
        expected = {"p99_budget": {"within_budget": True}}
        with patch(
            "latency_dashboard.run_live_dashboard",
            return_value=expected,
        ):
            result = main([
                "--p99-budget-ns", "50000",
                "--fail-on-budget-exceeded",
            ])

        self.assertIs(result, expected)

    def test_render_graph_scales_bars_to_window_maximum(self):
        frame = render_frame([5, 10], completed=2, total=2, side="SELL", width=34)
        sample_lines = frame.splitlines()[-2:]

        self.assertEqual(sample_lines[0], "         5 ns | #####")
        self.assertEqual(sample_lines[1], "        10 ns | ##########")

    def test_render_frame_reports_buy_and_sell_window_statistics(self):
        frame = render_frame(
            [10, 20, 30],
            completed=3,
            total=3,
            side="BUY",
            samples_by_side={"BUY": [10, 30], "SELL": [20]},
        )

        self.assertIn("BUY median 20.0 ns, p99 30 ns", frame)
        self.assertIn("SELL median 20 ns, p99 20 ns", frame)

    def test_render_frame_reports_per_side_budget_state(self):
        frame = render_frame(
            [10, 15, 30],
            completed=3,
            total=3,
            side="SELL",
            samples_by_side={"BUY": [10, 15], "SELL": [30]},
            p99_budget_ns=20,
        )

        self.assertIn("BUY median 12.5 ns, p99 15 ns | budget within budget", frame)
        self.assertIn("SELL median 30 ns, p99 30 ns | budget OVER BUDGET", frame)

    def test_live_run_refreshes_and_keeps_only_configured_window(self):
        output = io.StringIO()

        def fake_measure(count, seed, warmup, on_sample):
            for update in (
                (10, 1, 3, "BUY"),
                (20, 2, 3, "SELL"),
                (30, 3, 3, "BUY"),
            ):
                on_sample(*update)
            return {"latency": {"count": 3}}

        with patch(
            "latency_dashboard.measure_engine_latency",
            side_effect=fake_measure,
        ):
            result = run_live_dashboard(
                count=3,
                window=2,
                refresh_every=1,
                output=output,
            )

        self.assertEqual(result["latency"]["count"], 3)
        self.assertIn("Progress: 3/3", output.getvalue())
        self.assertIn("Window: 2", output.getvalue())
        self.assertIn("30 ns", output.getvalue())
        self.assertIn("BUY median 20.0 ns, p99 30 ns", output.getvalue())
        self.assertIn("SELL median 20 ns, p99 20 ns", output.getvalue())

    def test_parser_accepts_dashboard_options(self):
        args = build_parser().parse_args([
            "--count", "20",
            "--warmup", "5",
            "--window", "8",
            "--refresh-every", "2",
            "--p99-budget-ns", "50000",
            "--fail-on-budget-exceeded",
            "--output", "latency-live.json",
        ])

        self.assertEqual(args.count, 20)
        self.assertEqual(args.warmup, 5)
        self.assertEqual(args.window, 8)
        self.assertEqual(args.refresh_every, 2)
        self.assertEqual(args.p99_budget_ns, 50000)
        self.assertTrue(args.fail_on_budget_exceeded)
        self.assertEqual(args.output, "latency-live.json")

    def test_output_option_saves_final_json_with_raw_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "latency-live.json"

            def fake_measure(count, seed, warmup, on_sample, include_samples):
                on_sample(12, 1, 1, "BUY")
                return {
                    "scope": "ChronosMatch.add_order call",
                    "latency": {"count": 1, "median_ns": 12},
                    "samples_ns": [12] if include_samples else None,
                }

            with patch(
                "latency_dashboard.measure_engine_latency",
                side_effect=fake_measure,
            ):
                result = run_live_dashboard(
                    count=1,
                    refresh_every=1,
                    output=io.StringIO(),
                    report_path=report_path,
                )

            saved = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved, result)
            self.assertEqual(saved["samples_ns"], [12])

    def test_saved_json_includes_p99_budget_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            for count, budget, expected in (
                (1, 20, True),
                (1, 19, False),
                (0, 20, None),
            ):
                with self.subTest(count=count, budget=budget):
                    report_path = Path(directory) / f"report-{count}-{budget}.json"

                    def fake_measure(
                        count, seed, warmup, on_sample, include_samples
                    ):
                        if count:
                            on_sample(20, 1, 1, "BUY")
                        p99_ns = 20 if count else None
                        return {
                            "latency": {"count": count, "p99_ns": p99_ns},
                            "latency_by_side": {
                                "BUY": {"p99_ns": p99_ns},
                                "SELL": {"p99_ns": None},
                            },
                            "samples_ns": [20] if include_samples and count else [],
                        }

                    with patch(
                        "latency_dashboard.measure_engine_latency",
                        side_effect=fake_measure,
                    ):
                        result = run_live_dashboard(
                            count=count,
                            output=io.StringIO(),
                            report_path=report_path,
                            p99_budget_ns=budget,
                        )

                    expected_budget = {
                        "limit_ns": budget,
                        "measured_ns": 20 if count else None,
                        "within_budget": expected,
                    }
                    self.assertEqual(result["p99_budget"], expected_budget)
                    self.assertEqual(
                        result["p99_budget_by_side"],
                        {
                            "BUY": expected_budget,
                            "SELL": {
                                "limit_ns": budget,
                                "measured_ns": None,
                                "within_budget": None,
                            },
                        },
                    )
                    saved = json.loads(report_path.read_text(encoding="utf-8"))
                    self.assertEqual(saved["p99_budget"], expected_budget)
                    self.assertEqual(
                        saved["p99_budget_by_side"],
                        result["p99_budget_by_side"],
                    )

    def test_output_option_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "latency-live.json"
            report_path.write_text("keep", encoding="utf-8")

            with patch(
                "latency_dashboard.measure_engine_latency",
                return_value={"latency": {"count": 0}},
            ):
                with self.assertRaises(FileExistsError):
                    run_live_dashboard(
                        count=0,
                        output=io.StringIO(),
                        report_path=report_path,
                    )

            self.assertEqual(report_path.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
