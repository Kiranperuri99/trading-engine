import unittest

from engine_summary import summarize_engine
from trading_engine import ChronosMatch, Order


class TestEngineSummary(unittest.TestCase):

    def test_summary_reports_trade_and_remaining_quantity(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 10))
        engine.add_order(Order(2, "SELL", 100.0, 4))

        result = summarize_engine(engine, 2)

        self.assertEqual(result, {
            "orders_processed": 2,
            "trade_count": 1,
            "traded_quantity": 4,
            "pending_buy_quantity": 6,
            "pending_sell_quantity": 0,
            "best_bid": 101.0,
            "best_ask": None,
            "spread": None,
        })

        # Producing a summary must not change the order book.
        self.assertEqual(engine.buy_orders[0].quantity, 6)
        self.assertEqual(len(engine.trades), 1)


if __name__ == "__main__":
    unittest.main()