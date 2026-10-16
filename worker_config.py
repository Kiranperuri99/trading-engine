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