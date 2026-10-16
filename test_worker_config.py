
from unittest.mock import Mock, patch
from worker_config import acquire_before, make_deadline
import unittest

from worker_config import validate_timeout


class TestWorkerConfig(unittest.TestCase):
    def test_deadline_uses_validated_timeout(self):
        with patch("worker_config.monotonic", return_value=100.0):
            self.assertEqual(make_deadline(5), 105.0)

    def test_expired_deadline_does_not_acquire_lock(self):
        lock = Mock()

        with patch("worker_config.monotonic", return_value=100.0):
            with self.assertRaises(TimeoutError):
                with acquire_before(lock, 99.0):
                    self.fail("Expired operation should not run")

        lock.acquire.assert_not_called()
        lock.release.assert_not_called()

    def test_lock_timeout_is_reported(self):
        lock = Mock()
        lock.acquire.return_value = False

        with patch("worker_config.monotonic", return_value=100.0):
            with self.assertRaises(TimeoutError):
                with acquire_before(lock, 105.0):
                    self.fail("Operation should not run without the lock")

        lock.acquire.assert_called_once_with(timeout=5.0)
        lock.release.assert_not_called()

    def test_lock_is_released_when_operation_fails(self):
        lock = Mock()
        lock.acquire.return_value = True

        with patch("worker_config.monotonic", return_value=100.0):
            with self.assertRaises(ValueError):
                with acquire_before(lock, 105.0):
                    raise ValueError("Operation failed")

        lock.release.assert_called_once_with()

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
