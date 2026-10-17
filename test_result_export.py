import json
import tempfile
import unittest
from pathlib import Path

from result_export import save_result


class TestResultExport(unittest.TestCase):

    def test_saved_result_preserves_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            result = {
                "scope": "engine call",
                "count": 2,
                "median_ns": 20.5,
                "missing": None,
            }

            save_result(path, result)

            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                result,
            )

    def test_existing_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text("keep this", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                save_result(path, {"count": 2})

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "keep this",
            )

    def test_non_finite_value_creates_no_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"

            with self.assertRaises(ValueError):
                save_result(path, {"median_ns": float("nan")})

            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()