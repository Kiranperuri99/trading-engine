from contextlib import contextmanager
from time import monotonic

from math import isfinite


def validate_timeout(seconds):
    if type(seconds) not in (int, float):
        raise ValueError("Timeout must be a number")

    try:
        value = float(seconds)
    except OverflowError:
        raise ValueError("Timeout is too large") from None

    if not isfinite(value) or value <= 0:
        raise ValueError("Timeout must be finite and greater than zero")

    return value
def make_deadline(timeout):
    return monotonic() + validate_timeout(timeout)


@contextmanager
def acquire_before(lock, deadline):
    remaining = deadline - monotonic()

    if remaining <= 0:
        raise TimeoutError("Worker deadline expired")

    if not lock.acquire(timeout=remaining):
        raise TimeoutError("Timed out waiting for the shared lock")

    try:
        yield
    finally:
        lock.release()