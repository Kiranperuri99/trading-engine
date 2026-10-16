import unittest
from unittest.mock import Mock, patch

from market_simulator import generate_orders
from simulation_workers import produce_orders


class TestSimulationWorkers(unittest.TestCase):

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