import unittest

from latency_stats import histogram_latencies, summarize_latencies


class TestLatencyStats(unittest.TestCase):

    def test_histogram_counts_samples_in_inclusive_latency_buckets(self):
        samples = [
            0, 1000, 1001, 5000, 5001, 10000,
            10001, 50000, 50001, 100000, 100001,
        ]

        self.assertEqual(
            histogram_latencies(samples),
            {
                "<=1000": 2,
                "1001-5000": 2,
                "5001-10000": 2,
                "10001-50000": 2,
                "50001-100000": 2,
                ">100000": 1,
            },
        )

    def test_empty_histogram_contains_zero_counts_for_all_buckets(self):
        self.assertEqual(
            histogram_latencies([]),
            {
                "<=1000": 0,
                "1001-5000": 0,
                "5001-10000": 0,
                "10001-50000": 0,
                "50001-100000": 0,
                ">100000": 0,
            },
        )

    def test_histogram_rejects_invalid_samples(self):
        for sample in (-1, True, 1.5, "10", None):
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    histogram_latencies([sample])

    def test_known_percentiles(self):
        result = summarize_latencies(range(1, 101))

        self.assertEqual(result, {
            "count": 100,
            "min_ns": 1,
            "median_ns": 50.5,
            "p95_ns": 95,
            "p99_ns": 99,
            "p99_9_ns":100, 
            "max_ns": 100,
        })
    def test_empty_samples(self):
        result = summarize_latencies([])

        self.assertEqual(result["count"], 0)
        for key in ("min_ns", "median_ns", "p95_ns", "p99_ns", "max_ns"):
            self.assertIsNone(result[key])
            self.assertIsNone(result["p99_9_ns"])

    def test_single_zero_sample(self):
        result = summarize_latencies([0])

        self.assertEqual(result["count"], 1)
        for key in ("min_ns", "median_ns", "p95_ns", "p99_ns", "max_ns"):
            self.assertEqual(result[key], 0)

    def test_unsorted_input_is_not_modified(self):
        samples = [30, 10, 20, 40]

        result = summarize_latencies(samples)

        self.assertEqual(samples, [30, 10, 20, 40])
        self.assertEqual(result["median_ns"], 25.0)
        self.assertEqual(result["p95_ns"], 40)

    def test_invalid_samples_are_rejected(self):
        for sample in (-1, True, 1.5, "10", None):
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    summarize_latencies([sample])
    def test_two_samples_use_upper_value_for_high_percentiles(self):
        result = summarize_latencies([10, 20])

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["median_ns"], 15)
        self.assertEqual(result["p95_ns"], 20)
        self.assertEqual(result["p99_ns"], 20)
        self.assertEqual(result["p99_9_ns"], 20)

    def test_percentiles_round_up_for_101_samples(self):
        result = summarize_latencies(range(1, 102))

        self.assertEqual(result["median_ns"], 51)
        self.assertEqual(result["p95_ns"], 96)
        self.assertEqual(result["p99_ns"], 100)
        self.assertEqual(result["max_ns"], 101)
        self.assertEqual(result["p99_9_ns"], 101)

    def test_repeated_latencies_keep_the_same_percentiles(self):
        result = summarize_latencies([25] * 20)

        self.assertEqual(result["count"], 20)
        self.assertEqual(result["min_ns"], 25)
        self.assertEqual(result["median_ns"], 25)
        self.assertEqual(result["p95_ns"], 25)
        self.assertEqual(result["p99_ns"], 25)
        self.assertEqual(result["max_ns"], 25)
        self.assertEqual(result["p99_9_ns"], 25)

if __name__ == "__main__":
    unittest.main()
