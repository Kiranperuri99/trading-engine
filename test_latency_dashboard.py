import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from latency_dashboard import (
    build_parser,
    render_frame,
    run_live_dashboard,
)


class TestLatencyDashboard(unittest.TestCase):
    def test_render_empty_dashboard(self):
        frame = render_frame([], completed=0, total=0, side=None)

        self.assertIn("Progress: 0/0", frame)
        self.assertIn("Waiting for the first measurement", frame)
        self.assertIn("median n/a", frame)

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
            "--output", "latency-live.json",
        ])

        self.assertEqual(args.count, 20)
        self.assertEqual(args.warmup, 5)
        self.assertEqual(args.window, 8)
        self.assertEqual(args.refresh_every, 2)
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
