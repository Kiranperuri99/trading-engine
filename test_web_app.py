"""HTTP integration tests for the local browser demo."""

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from web_app import TradingEngineService, create_server


class TestLocalWebApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = TradingEngineService()
        cls.server = create_server(port=0, service=cls.service)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.service.reset()

    def get_json(self, path):
        with urlopen(self.base_url + path, timeout=2) as response:
            return response.status, json.loads(response.read())

    def send_json(self, path, method, data):
        request = Request(
            self.base_url + path,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_homepage_serves_browser_interface(self):
        with urlopen(self.base_url + "/", timeout=2) as response:
            page = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn("Market overview", page)
        self.assertIn('id="order-form"', page)
        self.assertIn("Browser-only preview", page)

    def test_initial_state_has_demo_book_and_one_trade(self):
        status, state = self.get_json("/api/state")

        self.assertEqual(status, 200)
        self.assertEqual(state["execution"]["trade_count"], 1)
        self.assertEqual(state["execution"]["total_quantity"], 4)
        self.assertEqual(state["best_bid"], 101.25)
        self.assertEqual(state["best_ask"], 101.3)
        self.assertGreater(len(state["open_orders"]), 0)

    def test_order_submission_matches_engine_and_cancel_updates_state(self):
        status, state = self.send_json(
            "/api/orders",
            "POST",
            {"side": "BUY", "price": 101.3, "quantity": 2},
        )

        self.assertEqual(status, 201)
        self.assertEqual(state["execution"]["trade_count"], 2)
        self.assertEqual(state["execution"]["total_quantity"], 6)
        self.assertEqual(state["next_order_id"], 1009)

        status, state = self.send_json(
            "/api/orders", "POST", {"side": "SELL", "price": 103, "quantity": 3}
        )
        self.assertEqual(status, 201)
        order_id = state["open_orders"][-1]["order_id"]
        status, state = self.send_json(f"/api/orders/{order_id}", "DELETE", {})

        self.assertEqual(status, 200)
        self.assertTrue(state["cancelled"])
        self.assertNotIn(order_id, [order["order_id"] for order in state["open_orders"]])
    def test_cancellation_is_scoped_to_symbol(self):
        tcs_order_id = 9001
        infy_order_id = 9002

        status, tcs = self.send_json(
            "/api/orders",
            "POST",
            {
                "symbol": "TCS",
                "side": "BUY",
                "price": 1.0,
                "quantity": 1,
                "order_id": tcs_order_id,
            },
        )
        self.assertEqual(status, 201)
        self.assertIn(
            tcs_order_id, [order["order_id"] for order in tcs["open_orders"]]
        )

        status, infy = self.send_json(
            "/api/orders",
            "POST",
            {
                "symbol": "INFY",
                "side": "BUY",
                "price": 1.0,
                "quantity": 1,
                "order_id": infy_order_id,
            },
        )
        self.assertEqual(status, 201)
        self.assertIn(
            infy_order_id, [order["order_id"] for order in infy["open_orders"]]
        )

        status, cancelled_tcs = self.send_json(
            f"/api/orders/{tcs_order_id}?symbol=TCS", "DELETE", {}
        )
        self.assertEqual(status, 200)
        self.assertTrue(cancelled_tcs["cancelled"])
        self.assertNotIn(
            tcs_order_id,
            [order["order_id"] for order in cancelled_tcs["open_orders"]],
        )

        _, infy_after = self.get_json("/api/state?symbol=INFY")
        self.assertIn(
            infy_order_id, [order["order_id"] for order in infy_after["open_orders"]]
        )
    def test_invalid_order_returns_clear_error_without_mutating_engine(self):
        before = self.service.state()
        status, response = self.send_json(
            "/api/orders", "POST", {"side": "HOLD", "price": 100, "quantity": 1}
        )

        self.assertEqual(status, 400)
        self.assertIn("Side must be BUY or SELL", response["error"])
        self.assertEqual(self.service.state()["execution"], before["execution"])

    def test_reset_restores_seeded_demo(self):
        self.send_json("/api/orders", "POST", {"side": "BUY", "price": 99, "quantity": 3})
        status, state = self.send_json("/api/reset", "POST", {})

        self.assertEqual(status, 200)
        self.assertEqual(state["next_order_id"], 1008)
        self.assertEqual(state["execution"]["trade_count"], 1)


if __name__ == "__main__":
    unittest.main()
