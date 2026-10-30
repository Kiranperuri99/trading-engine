import io
import unittest
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

    def test_parser_accepts_dashboard_options(self):
        args = build_parser().parse_args([
            "--count", "20",
            "--warmup", "5",
            "--window", "8",
            "--refresh-every", "2",
        ])

        self.assertEqual(args.count, 20)
        self.assertEqual(args.warmup, 5)
        self.assertEqual(args.window, 8)
        self.assertEqual(args.refresh_every, 2)


if __name__ == "__main__":
    unittest.main()
