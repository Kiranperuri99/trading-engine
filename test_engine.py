import unittest
import io
from contextlib import redirect_stdout
from trading_engine import Order, ChronosMatch


class TestChronosMatch(unittest.TestCase):
    def test_same_price_buy_orders_match_oldest_first(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 1))
        engine.add_order(Order(2, "BUY", 101.0, 1))
        engine.add_order(Order(3, "SELL", 100.0, 1))

        self.assertEqual(
            [order.order_id for order in engine.buy_orders],
            [2],
        )
    def test_order_id_cannot_be_reused_after_filled(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 1))
        engine.add_order(Order(2, "SELL", 100.0, 1))

        with self.assertRaises(ValueError):
            engine.add_order(Order(1, "BUY", 99.0, 1))

    def test_order_id_cannot_be_reused_after_cancelled(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 99.0, 1))
        self.assertTrue(engine.cancel_order(1))

        with self.assertRaises(ValueError):
            engine.add_order(Order(1, "BUY", 98.0, 1))
    def test_oversized_price_preserves_existing_orders(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 5))

        with self.assertRaisesRegex(ValueError, "Price is too large"):
            engine.add_order(Order(2, "BUY", 10**1000, 3))

        self.assertEqual(engine.buy_orders, [])
        self.assertEqual(len(engine.sell_orders), 1)
        self.assertEqual(engine.sell_orders[0].order_id, 1)
        self.assertEqual(engine.sell_orders[0].quantity, 5)
        self.assertEqual(engine.trades, [])

    def test_incoming_sell_uses_each_waiting_buy_price(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 3))
        engine.add_order(Order(2, "BUY", 103.0, 2))

        engine.add_order(Order(3, "SELL", 100.0, 4))

        self.assertEqual(engine.trades, [
            {
                "buy_order_id": 2,
                "sell_order_id": 3,
                "price": 103.0,
                "quantity": 2,
            },
            {
                "buy_order_id": 1,
                "sell_order_id": 3,
                "price": 101.0,
                "quantity": 2,
            },
        ])
        self.assertEqual(len(engine.buy_orders), 1)
        self.assertEqual(engine.buy_orders[0].order_id, 1)
        self.assertEqual(engine.buy_orders[0].quantity, 1)
        self.assertEqual(engine.sell_orders, [])

    def test_incoming_buy_uses_each_waiting_sell_price(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 103.0, 3))
        engine.add_order(Order(2, "SELL", 101.0, 2))

        engine.add_order(Order(3, "BUY", 104.0, 4))

        self.assertEqual(engine.trades, [
            {
                "buy_order_id": 3,
                "sell_order_id": 2,
                "price": 101.0,
                "quantity": 2,
            },
            {
                "buy_order_id": 3,
                "sell_order_id": 1,
                "price": 103.0,
                "quantity": 2,
            },
        ])
        self.assertEqual(len(engine.sell_orders), 1)
        self.assertEqual(engine.sell_orders[0].order_id, 1)
        self.assertEqual(engine.sell_orders[0].quantity, 1)
        self.assertEqual(engine.buy_orders, [])

    def test_incoming_buy_uses_waiting_sell_price(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 5))
        engine.add_order(Order(2, "BUY", 105.0, 5))

        self.assertEqual(engine.trades, [{
            "buy_order_id": 2,
            "sell_order_id": 1,
            "price": 100.0,
            "quantity": 5,
        }])


    def test_matching_orders(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 101.0, 10))
        engine.add_order(Order(2, "SELL", 100.0, 5))

        self.assertEqual(len(engine.buy_orders), 1)
        self.assertEqual(engine.buy_orders[0].quantity, 5)
        self.assertEqual(len(engine.sell_orders), 0)

    def test_orders_do_not_match(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 99.0, 10))
        engine.add_order(Order(2, "SELL", 100.0, 5))

        self.assertEqual(len(engine.buy_orders), 1)
        self.assertEqual(len(engine.sell_orders), 1)

    def test_rejects_non_positive_quantity(self):
        for quantity in (0, -5):
            with self.subTest(quantity=quantity):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, "BUY", 100.0, quantity))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
    def test_rejects_invalid_price(self):
        for price in (0, -10, float("nan"), float("inf"), float("-inf")):
            with self.subTest(price=price):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, "BUY", price, 5))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
    def test_rejects_non_integer_quantity(self):
        for quantity in (2.5, "5", True, None):
            with self.subTest(quantity=quantity):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, "BUY", 100.0, quantity))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
    def test_rejects_invalid_order_id(self):
        for order_id in (0, -1, 1.5, "1", True, None):
            with self.subTest(order_id=order_id):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(order_id, "BUY", 100.0, 5))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, []) 
    def test_accepts_side_with_spaces_and_lowercase(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, " buy ", 100.0, 5))
        engine.add_order(Order(2, " sell ", 100.0, 5))

        self.assertEqual(engine.buy_orders, [])
        self.assertEqual(engine.sell_orders, [])

    def test_rejects_invalid_side(self):
        for side in ("HOLD", "", "   ", None, 123):
            with self.subTest(side=side):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, side, 100.0, 5))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
    def test_rejects_invalid_price_types(self):
        for price in ("100", True, False, None):
            with self.subTest(price=price):
                engine = ChronosMatch()

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, "BUY", price, 5))

                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, []) 
    def test_records_completed_trade(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 101.0, 10))
        engine.add_order(Order(2, "SELL", 100.0, 5))

        self.assertEqual(engine.trades, [{
            "buy_order_id": 1,
            "sell_order_id": 2,
            "price": 101.0,
            "quantity": 5,
        }])

    def test_no_trade_recorded_when_prices_do_not_cross(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 99.0, 10))
        engine.add_order(Order(2, "SELL", 100.0, 5))

        self.assertEqual(engine.trades, [])
    def test_best_prices_for_empty_book(self):
        engine = ChronosMatch()

        self.assertIsNone(engine.best_bid())
        self.assertIsNone(engine.best_ask())

    def test_best_prices_update_after_matching(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 98.0, 5))
        engine.add_order(Order(2, "BUY", 99.0, 5))
        engine.add_order(Order(3, "SELL", 103.0, 5))
        engine.add_order(Order(4, "SELL", 102.0, 5))

        self.assertEqual(engine.best_bid(), 99.0)
        self.assertEqual(engine.best_ask(), 102.0)

        engine.add_order(Order(5, "BUY", 102.0, 5))

        self.assertEqual(engine.best_bid(), 99.0)
        self.assertEqual(engine.best_ask(), 103.0)    
    def test_spread_between_best_prices(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 99.0, 5))
        engine.add_order(Order(2, "SELL", 102.0, 5))

        self.assertEqual(engine.spread(), 3.0)

    def test_spread_requires_both_sides(self):
        engine = ChronosMatch()
        self.assertIsNone(engine.spread())

        engine.add_order(Order(1, "BUY", 99.0, 5))
        self.assertIsNone(engine.spread())

        engine = ChronosMatch()
        engine.add_order(Order(2, "SELL", 102.0, 5))
        self.assertIsNone(engine.spread())     
    def test_cancel_waiting_order(self):
        for side in ("BUY", "SELL"):
            with self.subTest(side=side):
                engine = ChronosMatch()
                engine.add_order(Order(1, side, 100.0, 5))

                self.assertTrue(engine.cancel_order(1))
                self.assertEqual(engine.buy_orders, [])
                self.assertEqual(engine.sell_orders, [])
                self.assertEqual(engine.trades, [])

    def test_cancel_unknown_order_preserves_book(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 100.0, 5))

        self.assertFalse(engine.cancel_order(999))
        self.assertEqual(len(engine.buy_orders), 1)
        self.assertEqual(engine.buy_orders[0].order_id, 1)
        self.assertEqual(engine.buy_orders[0].quantity, 5)
    def test_rejects_duplicate_active_order_id(self):
        for side in ("BUY", "SELL"):
            with self.subTest(side=side):
                engine = ChronosMatch()
                engine.add_order(Order(1, "BUY", 100.0, 5))

                with self.assertRaises(ValueError):
                    engine.add_order(Order(1, side, 100.0, 3))

                self.assertEqual(len(engine.buy_orders), 1)
                self.assertEqual(engine.buy_orders[0].quantity, 5)
                self.assertEqual(engine.sell_orders, [])
                self.assertEqual(engine.trades, [])
    def test_total_traded_quantity_starts_at_zero(self):
        engine = ChronosMatch()

        self.assertEqual(engine.total_traded_quantity(), 0)

    def test_total_traded_quantity_across_multiple_matches(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "SELL", 100.0, 3))
        engine.add_order(Order(2, "SELL", 101.0, 4))
        engine.add_order(Order(3, "BUY", 101.0, 10))

        self.assertEqual(len(engine.trades), 2)
        self.assertEqual(engine.total_traded_quantity(), 7)
        self.assertEqual(engine.buy_orders[0].quantity, 3)
        self.assertEqual(engine.sell_orders, [])
    def test_pending_quantities_for_empty_book(self):
        engine = ChronosMatch()

        self.assertEqual(
            engine.pending_quantities(),
            {"BUY": 0, "SELL": 0},
        )

    def test_pending_quantities_after_match_and_cancel(self):
        engine = ChronosMatch()
        engine.add_order(Order(1, "BUY", 100.0, 10))
        engine.add_order(Order(2, "BUY", 99.0, 4))
        engine.add_order(Order(3, "SELL", 101.0, 6))

        self.assertEqual(
            engine.pending_quantities(),
            {"BUY": 14, "SELL": 6},
        )

        engine.add_order(Order(4, "SELL", 100.0, 3))

        self.assertEqual(
            engine.pending_quantities(),
            {"BUY": 11, "SELL": 6},
        )

        engine.cancel_order(2)

        self.assertEqual(
            engine.pending_quantities(),
            {"BUY": 7, "SELL": 6},
        )
    def test_cancel_rejects_invalid_order_id(self):
        for order_id in (True, 1.0, "1", None, 0, -1):
            with self.subTest(order_id=order_id):
                engine = ChronosMatch()
                engine.add_order(Order(1, "BUY", 100.0, 5))

                with self.assertRaises(ValueError):
                    engine.cancel_order(order_id)

                self.assertEqual(len(engine.buy_orders), 1)
                self.assertEqual(engine.buy_orders[0].order_id, 1)
                self.assertEqual(engine.buy_orders[0].quantity, 5) 
    def test_same_price_buy_orders_match_in_arrival_order(self):
        engine = ChronosMatch()
        engine.add_order(Order(20, "BUY", 100.0, 3))
        engine.add_order(Order(10, "BUY", 100.0, 4))
        engine.add_order(Order(30, "SELL", 100.0, 5))

        self.assertEqual(
            [trade["buy_order_id"] for trade in engine.trades],
            [20, 10],
        )
        self.assertEqual(
            [trade["quantity"] for trade in engine.trades],
            [3, 2],
        )
        self.assertEqual(len(engine.buy_orders), 1)
        self.assertEqual(engine.buy_orders[0].order_id, 10)
        self.assertEqual(engine.buy_orders[0].quantity, 2)

    def test_same_price_sell_orders_match_in_arrival_order(self):
        engine = ChronosMatch()
        engine.add_order(Order(20, "SELL", 100.0, 3))
        engine.add_order(Order(10, "SELL", 100.0, 4))
        engine.add_order(Order(30, "BUY", 100.0, 5))

        self.assertEqual(
            [trade["sell_order_id"] for trade in engine.trades],
            [20, 10],
        )
        self.assertEqual(
            [trade["quantity"] for trade in engine.trades],
            [3, 2],
        )
        self.assertEqual(len(engine.sell_orders), 1)
        self.assertEqual(engine.sell_orders[0].order_id, 10)
        self.assertEqual(engine.sell_orders[0].quantity, 2)
    def test_quiet_mode_still_matches_orders(self):
        output = io.StringIO()
        engine = ChronosMatch(verbose=False)

        with redirect_stdout(output):
            engine.add_order(Order(1, "BUY", 100.0, 5))
            engine.add_order(Order(2, "SELL", 100.0, 5))

        self.assertEqual(output.getvalue(), "")
        self.assertEqual(engine.total_traded_quantity(), 5)
        self.assertEqual(engine.buy_orders, [])
        self.assertEqual(engine.sell_orders, [])
    def test_incoming_buy_uses_waiting_sell_price(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 5))
        engine.add_order(Order(2, "BUY", 105.0, 5))

        self.assertEqual(engine.trades, [{
            "buy_order_id": 2,
            "sell_order_id": 1,
            "price": 100.0,
            "quantity": 5,
        }])

if __name__ == "__main__":
    unittest.main()