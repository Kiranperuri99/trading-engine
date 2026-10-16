import unittest

from worker_config import validate_timeout


class TestWorkerConfig(unittest.TestCase):

    def test_positive_timeout_is_accepted(self):
        self.assertEqual(validate_timeout(15), 15.0)
        self.assertEqual(validate_timeout(0.5), 0.5)

    def test_invalid_timeout_is_rejected(self):
        for value in (
            0,
            -1,
            True,
            "15",
            None,
            float("nan"),
            float("inf"),
            float("-inf"),
            10**1000,
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_timeout(value)


if __name__ == "__main__":
    unittest.main()
    