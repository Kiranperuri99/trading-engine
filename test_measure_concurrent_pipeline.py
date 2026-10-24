import io
from contextlib import redirect_stdout
from unittest.mock import patch
from measure_concurrent_pipeline import main
from datetime import datetime, timezone
from unittest.mock import patch
import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch
from measure_concurrent_pipeline import main

from measure_concurrent_pipeline import measure_concurrent_pipeline


class TestMeasureConcurrentPipeline(unittest.TestCase):
    def test_cli_passes_selected_settings_to_benchmark(self):
        with patch(
            "measure_concurrent_pipeline.measure_concurrent_pipeline",
            return_value={"orders_processed": 50},
        ) as benchmark:
            with redirect_stdout(io.StringIO()):
                main([
                    "--count", "50",
                    "--seed", "7",
                    "--capacity", "4",
                    "--timeout", "20",
                ])

        benchmark.assert_called_once_with(
            count=50,
            seed=7,
            capacity=4,
            timeout=20.0,
        )
    def test_report_includes_environment_details(self):
        with patch(
            "measure_concurrent_pipeline.run_concurrent",
            return_value={"orders_processed": 0},
        ):
            result = measure_concurrent_pipeline(count=0)

        environment = result["environment"]
        self.assertIn("python_version", environment)
        self.assertIn("operating_system", environment)
        self.assertIn("machine", environment)
        self.assertIn("pointer_bits", environment)
        self.assertIsInstance(environment["pointer_bits"], int)
    def test_output_option_saves_json_report(self):
        expected = {"schema_version": 1, "orders_per_second": 12.5}

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.json"

            with patch(
                "measure_concurrent_pipeline.measure_concurrent_pipeline",
                return_value=expected,
            ):
                with redirect_stdout(io.StringIO()):
                    main(["--output", str(output_path)])

            saved = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved, expected)
    def test_report_has_version_and_utc_timestamp(self):
        with patch(
            "measure_concurrent_pipeline.run_concurrent",
            return_value={"orders_processed": 0},
        ):
            result = measure_concurrent_pipeline(count=0)

        self.assertEqual(result["schema_version"], 1)
        timestamp = datetime.fromisoformat(result["generated_at_utc"])
        self.assertEqual(timestamp.utcoffset(), timezone.utc.utcoffset(timestamp))
    def test_output_option_saves_json_report(self):
        expected = {"orders_processed": 0}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            output = io.StringIO()

            with patch(
                "measure_concurrent_pipeline.measure_concurrent_pipeline",
                return_value=expected,
            ):
                with redirect_stdout(output):
                    from measure_concurrent_pipeline import main
                    main(["--count", "0", "--output", str(path)])

            self.assertEqual(json.loads(path.read_text()), expected)
            self.assertEqual(json.loads(output.getvalue()), expected)

    def test_reports_elapsed_time_and_throughput(self):
        summary = {"orders_processed": 10}

        with patch(
            "measure_concurrent_pipeline.run_concurrent",
            return_value=summary,
        ) as runner:
            with patch(
                "measure_concurrent_pipeline.perf_counter_ns",
                side_effect=[100, 1100],
            ):
                result = measure_concurrent_pipeline(
                    count=10,
                    seed=7,
                    capacity=2,
                    timeout=5,
                )

        self.assertEqual(result["elapsed_ns"], 1000)
        self.assertEqual(result["orders_per_second"], 10_000_000.0)
        self.assertEqual(result["summary"], summary)
        runner.assert_called_once_with(
            count=10,
            seed=7,
            capacity=2,
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()