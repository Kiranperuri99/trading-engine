from simulation_workers import consume_orders
from trading_engine import Order
import unittest
from unittest.mock import Mock, patch

from market_simulator import generate_orders
from simulation_workers import produce_orders


class TestSimulationWorkers(unittest.TestCase):
    def test_consumer_waits_then_matches_orders(self):
        queue = Mock()
        queue.try_get_before.side_effect = [
            None,
            Order(1, "BUY", 101.0, 10),
            Order(2, "SELL", 100.0, 4),
        ]

        with patch("simulation_workers.sleep") as pause:
            result = consume_orders(queue, 2)

        self.assertEqual(result["orders_processed"], 2)
        self.assertEqual(result["trade_count"], 1)
        self.assertEqual(result["traded_quantity"], 4)
        self.assertEqual(result["pending_buy_quantity"], 6)
        self.assertEqual(result["pending_sell_quantity"], 0)
        pause.assert_called_once_with(0.001)

    def test_consumer_reports_queue_timeout(self):
        queue = Mock()
        queue.try_get_before.side_effect = TimeoutError("Queue timed out")

        with self.assertRaises(TimeoutError):
            consume_orders(queue, 1)

    def test_zero_count_consumer_does_not_read_queue(self):
        queue = Mock()

        result = consume_orders(queue, 0)

        queue.try_get_before.assert_not_called()
        self.assertEqual(result["orders_processed"], 0)
        self.assertEqual(result["trade_count"], 0)

    def test_consumer_rejects_invalid_count(self):
        for count in (-1, True, 2.5, "2", 1 << 64):
            with self.subTest(count=count):
                queue = Mock()

                with self.assertRaises(ValueError):
                    consume_orders(queue, count)

                queue.try_get_before.assert_not_called()

    def test_producer_sends_generated_orders_in_order(self):
        queue = Mock()
        queue.try_put_before.return_value = True

        with patch(
            "simulation_workers.make_deadline",
            return_value=123.0,
        ):
            produced = produce_orders(queue, 3, seed=7)

        expected = list(generate_orders(3, seed=7))
        calls = queue.try_put_before.call_args_list

        self.assertEqual(produced, 3)
        self.assertEqual(
            [call.args[0] for call in calls],
            expected,
        )
        self.assertTrue(
            all(call.args[1] == 123.0 for call in calls)
        )

    def test_producer_retries_same_order_when_full(self):
        queue = Mock()
        queue.try_put_before.side_effect = [False, True]

        with patch("simulation_workers.sleep") as pause:
            produced = produce_orders(queue, 1)

        calls = queue.try_put_before.call_args_list
        self.assertEqual(produced, 1)
        self.assertIs(calls[0].args[0], calls[1].args[0])
        pause.assert_called_once_with(0.001)

    def test_producer_reports_queue_timeout(self):
        queue = Mock()
        queue.try_put_before.side_effect = TimeoutError("Queue timed out")

        with self.assertRaises(TimeoutError):
            produce_orders(queue, 1)


if __name__ == "__main__":
    unittest.main()