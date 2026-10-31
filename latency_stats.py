from math import ceil
from statistics import median


LATENCY_HISTOGRAM_BUCKETS = (
    ("<=1000", 1_000),
    ("1001-5000", 5_000),
    ("5001-10000", 10_000),
    ("10001-50000", 50_000),
    ("50001-100000", 100_000),
    (">100000", None),
)


def histogram_latencies(samples):
    values = list(samples)
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("Latency samples must be non-negative integers")

    histogram = {label: 0 for label, _ in LATENCY_HISTOGRAM_BUCKETS}
    for value in values:
        for label, upper_bound in LATENCY_HISTOGRAM_BUCKETS:
            if upper_bound is None or value <= upper_bound:
                histogram[label] += 1
                break
    return histogram


def summarize_latencies(samples):
    values = list(samples)

    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("Latency samples must be non-negative integers")

    values.sort()
    count = len(values)

    if count == 0:
        return {
            "count": 0,
            "min_ns": None,
            "median_ns": None,
            "p95_ns": None,
            "p99_ns": None,
            "p99_9_ns": None,
            "max_ns": None,
        }

    def percentile(percent):
        rank = ceil(percent * count / 100)
        return values[rank - 1]

    return {
        "count": count,
        "min_ns": values[0],
        "median_ns": median(values),
        "p95_ns": percentile(95),
        "p99_ns": percentile(99),
        "p99_9_ns": percentile(99.9),
        "max_ns": values[-1],
    }
