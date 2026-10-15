import unittest

from market_simulator import generate_orders
from run_simulation import run_simulation


class TestRunSimulation(unittest.TestCase):

    def test_summary_counts_all_orders_and_quantities(self):
        count = 37
        seed = 42
        submitted = sum(
            order.quantity
            for order in generate_orders(count, seed)
        )

        result = run_simulation(count, seed)

        self.assertEqual(result["orders_processed"], count)
        self.assertEqual(
            submitted,
            result["pending_buy_quantity"]
            + result["pending_sell_quantity"]
            + 2 * result["traded_quantity"],
        )

    def test_empty_simulation_returns_empty_summary(self):
        result = run_simulation(0)

        self.assertEqual(result["orders_processed"], 0)
        self.assertEqual(result["trade_count"], 0)
        self.assertEqual(result["traded_quantity"], 0)
        self.assertEqual(result["pending_buy_quantity"], 0)
        self.assertEqual(result["pending_sell_quantity"], 0)
        self.assertIsNone(result["best_bid"])
        self.assertIsNone(result["best_ask"])
        self.assertIsNone(result["spread"])


if __name__ == "__main__":
    unittest.main()