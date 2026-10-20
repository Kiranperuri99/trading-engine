import unittest
import io
from contextlib import redirect_stdout
from trading_engine import Order, ChronosMatch


class TestChronosMatch(unittest.TestCase):
    def test_open_order_snapshot_after_partial_fill(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 100.0, 5))
        engine.add_order(Order(2, "SELL", 100.0, 2))

        snapshot = engine.get_open_order(1)
        self.assertEqual(snapshot, {
            "order_id": 1,
            "side": "BUY",
            "price": 100.0,
            "quantity": 3,
        })

        snapshot["quantity"] = 999
        self.assertEqual(engine.get_remaining_quantity(1), 3)
        self.assertIsNone(engine.get_open_order(2))
        self.assertIsNone(engine.get_open_order(999))

        engine.cancel_order(1)
        self.assertIsNone(engine.get_open_order(1))
    def test_reducing_partially_filled_sell_preserves_fifo(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 5))
        engine.add_order(Order(2, "SELL", 100.0, 4))
        engine.add_order(Order(3, "BUY", 100.0, 2))

        self.assertTrue(engine.reduce_order_quantity(1, 1))
        engine.add_order(Order(4, "BUY", 100.0, 2))

        self.assertEqual(
            [trade["sell_order_id"] for trade in engine.trades],
            [1, 1, 2],
        )
        self.assertEqual(engine.get_filled_quantity(1), 3)
        self.assertEqual(engine.get_remaining_quantity(2), 3)

    def test_reduction_cannot_exceed_remaining_after_fill(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 5))
        engine.add_order(Order(2, "BUY", 100.0, 3))

        with self.assertRaises(ValueError):
            engine.reduce_order_quantity(1, 3)

        self.assertEqual(engine.get_remaining_quantity(1), 2)
        self.assertEqual(engine.get_filled_quantity(1), 3)
    def test_quantity_reduction_preserves_fifo(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 100.0, 5))
        engine.add_order(Order(2, "BUY", 100.0, 5))

        self.assertTrue(engine.reduce_order_quantity(1, 2))
        engine.add_order(Order(3, "SELL", 100.0, 3))

        self.assertEqual(
            [trade["buy_order_id"] for trade in engine.trades],
            [1, 2],
        )
        self.assertEqual(
            [trade["quantity"] for trade in engine.trades],
            [2, 1],
        )

    def test_invalid_reduction_preserves_quantity(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 100.0, 5))

        for quantity in (0, -1, True, 1.5, "1", None, 6):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    engine.reduce_order_quantity(1, quantity)

                self.assertEqual(engine.get_remaining_quantity(1), 5)

        self.assertFalse(engine.reduce_order_quantity(999, 1))
    def test_bulk_cancel_selects_one_side(self):
        for side, remaining_id in ((" buy ", 2), (" sell ", 1)):
            with self.subTest(side=side):
                engine = ChronosMatch(verbose=False)
                engine.add_order(Order(1, "BUY", 99.0, 3))
                engine.add_order(Order(2, "SELL", 101.0, 4))

                self.assertEqual(engine.cancel_all_orders(side=side), 1)

                remaining = engine.buy_orders + engine.sell_orders
                self.assertEqual(
                    [order.order_id for order in remaining],
                    [remaining_id],
                )

    def test_invalid_bulk_cancel_side_preserves_orders(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 99.0, 3))

        for invalid_side in ("INVALID", "", 0, True):
            with self.subTest(side=invalid_side):
                with self.assertRaises(ValueError):
                    engine.cancel_all_orders(side=invalid_side)

                self.assertEqual(len(engine.buy_orders), 1)
    def test_matching_conserves_quantities_across_partial_fills(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 105.0, 7))
        engine.add_order(Order(2, "BUY", 104.0, 5))
        engine.add_order(Order(3, "SELL", 103.0, 4))
        engine.add_order(Order(4, "SELL", 104.0, 6))
        engine.add_order(Order(5, "SELL", 106.0, 3))

        traded = engine.total_traded_quantity()
        pending = engine.pending_quantities()

        self.assertEqual(traded, 10)
        self.assertEqual(traded + pending["BUY"], 12)
        self.assertEqual(traded + pending["SELL"], 13)
    def test_returned_trade_history_cannot_change_engine_records(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 100.0, 3))
        engine.add_order(Order(2, "SELL", 100.0, 1))

        reported_trades = engine.get_trades_for_order(1)
        reported_trades[0]["quantity"] = 999
        reported_trades[0]["price"] = 0.0
        reported_trades.clear()

        self.assertEqual(engine.get_filled_quantity(1), 1)
        self.assertEqual(engine.get_vwap(), 100.0)
        self.assertEqual(len(engine.get_trades_for_order(1)), 1)
    def test_cancel_all_orders_clears_both_sides(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 99.0, 3))
        engine.add_order(Order(2, "BUY", 98.0, 2))
        engine.add_order(Order(3, "SELL", 101.0, 4))

        self.assertEqual(engine.cancel_all_orders(), 3)
        self.assertEqual(engine.buy_orders, [])
        self.assertEqual(engine.sell_orders, [])
        self.assertEqual(engine.cancel_all_orders(), 0)

    def test_cancel_all_preserves_history_and_used_ids(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 100.0, 5))
        engine.add_order(Order(2, "SELL", 100.0, 2))
        history = [trade.copy() for trade in engine.trades]

        self.assertEqual(engine.cancel_all_orders(), 1)
        self.assertEqual(engine.trades, history)

        with self.assertRaises(ValueError):
            engine.add_order(Order(1, "BUY", 99.0, 1))
    def test_vwap_handles_large_finite_prices(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 1e308, 2))
        engine.add_order(Order(2, "SELL", 1.2e308, 1))
        engine.add_order(Order(3, "BUY", 1.3e308, 3))

        self.assertAlmostEqual(
            engine.get_vwap() / 1e308,
            3.2 / 3,
        )
    def test_order_lookups_reject_invalid_ids(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 100.0, 3))

        lookups = (
            engine.get_filled_quantity,
            engine.get_remaining_quantity,
            engine.get_trades_for_order,
            engine.get_open_order,
        )

        for lookup in lookups:
            for invalid_id in (0, -1, True, False, 1.0, 1.5, "1", None):
                with self.subTest(
                    method=lookup.__name__,
                    order_id=invalid_id,
                ):
                    with self.assertRaises(ValueError):
                        lookup(invalid_id)
    def test_mid_price_handles_large_finite_prices(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 1e308, 1))
        engine.add_order(Order(2, "SELL", 1.2e308, 1))

        midpoint = engine.get_mid_price()

        self.assertAlmostEqual(midpoint / 1e308, 1.1)
    def test_rejected_orders_do_not_reserve_order_ids(self):
        invalid_orders = [
            Order(1, "BUY", 100.0, 0),
            Order(1, "BUY", 0.0, 1),
            Order(1, "INVALID", 100.0, 1),
        ]

        for invalid_order in invalid_orders:
            with self.subTest(order=invalid_order):
                engine = ChronosMatch(verbose=False)

                with self.assertRaises(ValueError):
                    engine.add_order(invalid_order)

                self.assertNotIn(1, engine.seen_order_ids)

                engine.add_order(Order(1, "BUY", 100.0, 1))

                self.assertEqual(len(engine.buy_orders), 1)
                self.assertEqual(engine.buy_orders[0].order_id, 1)
    def test_incoming_buy_trades_at_resting_sell_price(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 1))
        engine.add_order(Order(2, "BUY", 101.0, 1))

        self.assertEqual(engine.trades[0]["price"], 100.0)

    def test_incoming_sell_trades_at_resting_buy_price(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 1))
        engine.add_order(Order(2, "SELL", 100.0, 1))

        self.assertEqual(engine.trades[0]["price"], 101.0)
    def test_get_trades_for_partially_filled_order(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 2))
        engine.add_order(Order(2, "SELL", 101.0, 1))
        engine.add_order(Order(3, "BUY", 102.0, 3))

        trades = engine.get_trades_for_order(3)

        self.assertEqual([trade["quantity"] for trade in trades], [2, 1])
        self.assertEqual(engine.get_trades_for_order(999), [])
    def test_vwap_weights_trade_prices_by_quantity(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 2))
        engine.add_order(Order(2, "SELL", 102.0, 1))
        engine.add_order(Order(3, "BUY", 103.0, 3))

        self.assertAlmostEqual(engine.get_vwap(), 302 / 3)

    def test_vwap_is_none_without_trades(self):
        engine = ChronosMatch(verbose=False)

        self.assertIsNone(engine.get_vwap())
    def test_remaining_quantity_after_partial_fill(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 5))
        engine.add_order(Order(2, "SELL", 100.0, 2))

        self.assertEqual(engine.get_remaining_quantity(1), 3)
        self.assertEqual(engine.get_remaining_quantity(2), 0)
    def test_filled_quantity_for_order(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 5))
        engine.add_order(Order(2, "SELL", 100.0, 2))
        engine.add_order(Order(3, "SELL", 100.0, 1))

        self.assertEqual(engine.get_filled_quantity(1), 3)
        self.assertEqual(engine.get_filled_quantity(2), 2)
        self.assertEqual(engine.get_filled_quantity(999), 0)
    def test_total_traded_quantity_counts_filled_units(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 5))
        engine.add_order(Order(2, "SELL", 100.0, 2))

        self.assertEqual(engine.get_total_traded_quantity(), 2)

    def test_total_traded_quantity_is_zero_without_trades(self):
        engine = ChronosMatch(verbose=False)

        self.assertEqual(engine.get_total_traded_quantity(), 0)
    def test_spread_is_best_ask_minus_best_bid(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 99.0, 1))
        engine.add_order(Order(2, "SELL", 101.0, 1))

        self.assertEqual(engine.get_spread(), 2.0)

    def test_spread_is_none_when_one_side_is_empty(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 101.0, 1))

        self.assertIsNone(engine.get_spread())
    def test_mid_price_is_average_of_best_bid_and_ask(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 99.0, 1))
        engine.add_order(Order(2, "SELL", 101.0, 1))

        self.assertEqual(engine.get_mid_price(), 100.0)

    def test_mid_price_is_none_when_one_side_is_empty(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 99.0, 1))

        self.assertIsNone(engine.get_mid_price())
    def test_order_book_depth_limits_price_levels(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 105.0, 1))
        engine.add_order(Order(2, "BUY", 104.0, 2))
        engine.add_order(Order(3, "SELL", 106.0, 3))
        engine.add_order(Order(4, "SELL", 107.0, 4))

        self.assertEqual(
            engine.get_order_book(depth=1),
            {
                "bids": [{"price": 105.0, "quantity": 1}],
                "asks": [{"price": 106.0, "quantity": 3}],
            },
        )

    def test_order_book_rejects_zero_depth(self):
        engine = ChronosMatch(verbose=False)

        with self.assertRaises(ValueError):
            engine.get_order_book(depth=0)
    def test_order_book_snapshot_stays_unchanged(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 2))

        snapshot = engine.get_order_book()
        engine.add_order(Order(2, "BUY", 100.0, 1))

        self.assertEqual(
            snapshot,
            {"bids": [{"price": 101.0, "quantity": 2}], "asks": []},
        )
    def test_order_book_groups_and_sorts_prices(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 101.0, 2))
        engine.add_order(Order(2, "BUY", 101.0, 4))
        engine.add_order(Order(3, "BUY", 100.0, 3))
        engine.add_order(Order(4, "SELL", 102.0, 1))
        engine.add_order(Order(5, "SELL", 103.0, 2))

        self.assertEqual(
        engine.get_order_book(),
            {
                "bids": [
                    {"price": 101.0, "quantity": 6},
                    {"price": 100.0, "quantity": 3},
                ],
                "asks": [
                    {"price": 102.0, "quantity": 1},
                    {"price": 103.0, "quantity": 2},
                ],
            },
        )
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
    def test_same_price_sell_orders_match_oldest_first(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "SELL", 100.0, 1))
        engine.add_order(Order(2, "SELL", 100.0, 1))
        engine.add_order(Order(3, "BUY", 101.0, 1))

        self.assertEqual(
            [order.order_id for order in engine.sell_orders],
            [2],
        )
    def test_book_summary_counts_orders_and_quantity(self):
        engine = ChronosMatch(verbose=False)
        engine.add_order(Order(1, "BUY", 99.0, 3))
        engine.add_order(Order(2, "BUY", 98.0, 4))
        engine.add_order(Order(3, "SELL", 105.0, 2))

        self.assertEqual(
            engine.get_book_summary(),
            {
                "BUY": {"order_count": 2, "total_quantity": 7},
                "SELL": {"order_count": 1, "total_quantity": 2},
            },
        )
if __name__ == "__main__":
    unittest.main()