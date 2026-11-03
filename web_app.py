"""Run the ChronosMatch simulator with a local browser interface."""

import argparse
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from trading_engine import ChronosMatch, Order


WEB_ROOT = Path(__file__).with_name("web")


class TradingEngineService:
    """Thread-safe adapter between the matching engine and the browser UI."""

    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self):
        with self._lock:
            self.engine = ChronosMatch(verbose=False)
            # A small deterministic sample makes the first screen useful.
            sample_orders = (
                Order(1000, "SELL", 101.30, 6),
                Order(1001, "BUY", 101.35, 4),
                Order(1002, "BUY", 101.25, 12),
                Order(1003, "BUY", 101.20, 18),
                Order(1004, "BUY", 101.10, 10),
                Order(1005, "SELL", 101.45, 8),
                Order(1006, "SELL", 101.50, 16),
                Order(1007, "SELL", 101.65, 20),
            )
            for order in sample_orders:
                self.engine.add_order(order)

    def _open_orders(self):
        orders = []
        for side, book in (("BUY", self.engine.buy_orders), ("SELL", self.engine.sell_orders)):
            orders.extend(
                {
                    "order_id": order.order_id,
                    "side": side,
                    "price": order.price,
                    "quantity": order.quantity,
                }
                for order in book
            )
        return sorted(
            orders,
            key=lambda order: (
                order["side"] != "BUY",
                -order["price"] if order["side"] == "BUY" else order["price"],
                order["order_id"],
            ),
        )

    def state(self):
        with self._lock:
            return {
                "book": self.engine.get_order_book(),
                "best_bid": self.engine.best_bid(),
                "best_ask": self.engine.best_ask(),
                "spread": self.engine.get_spread(),
                "mid_price": self.engine.get_mid_price(),
                "imbalance": self.engine.get_book_imbalance(),
                "book_summary": self.engine.get_book_summary(),
                "execution": self.engine.get_execution_summary(),
                "status_counts": self.engine.get_order_status_counts(),
                "open_orders": self._open_orders(),
                "trades": self.engine.get_recent_trades(limit=30),
                "next_order_id": max(self.engine.seen_order_ids, default=999) + 1,
            }

    @staticmethod
    def _positive_int(value, label):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{label} must be a positive whole number")
        return value

    def submit_order(self, data):
        if not isinstance(data, dict):
            raise ValueError("Order body must be a JSON object")
        with self._lock:
            order_id = data.get("order_id")
            if order_id in (None, ""):
                order_id = max(self.engine.seen_order_ids, default=999) + 1
            else:
                if isinstance(order_id, str) and order_id.isdigit():
                    order_id = int(order_id)
                self._positive_int(order_id, "Order ID")

            quantity = data.get("quantity")
            if isinstance(quantity, str) and quantity.isdigit():
                quantity = int(quantity)
            self._positive_int(quantity, "Quantity")

            price = data.get("price")
            if isinstance(price, str):
                try:
                    price = float(price)
                except ValueError:
                    raise ValueError("Price must be a positive number") from None
            if isinstance(price, bool) or not isinstance(price, (int, float)):
                raise ValueError("Price must be a positive number")

            side = data.get("side")
            if not isinstance(side, str) or side.strip().upper() not in ("BUY", "SELL"):
                raise ValueError("Side must be BUY or SELL")

            self.engine.add_order(Order(order_id, side, price, quantity))
            return self.state()

    def cancel_order(self, order_id):
        with self._lock:
            cancelled = self.engine.cancel_order(order_id)
            return cancelled, self.state()


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ChronosMatchLocal/1.0"

        def _send_bytes(self, status, payload, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, status, data):
            payload = json.dumps(data, allow_nan=False).encode("utf-8")
            self._send_bytes(status, payload, "application/json; charset=utf-8")

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ValueError("Invalid content length") from None
            if length <= 0 or length > 64_000:
                raise ValueError("Request body is empty or too large")
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("Request body must contain valid JSON") from None

        def _send_static(self, request_path):
            relative_path = unquote(request_path.lstrip("/")) or "index.html"
            root = WEB_ROOT.resolve()
            file_path = (root / relative_path).resolve()
            if file_path != root and root not in file_path.parents:
                self._send_json(404, {"error": "Not found"})
                return
            if not file_path.is_file():
                self._send_json(404, {"error": "Not found"})
                return
            content_type, _ = mimetypes.guess_type(file_path.name)
            content_type = content_type or "application/octet-stream"
            self._send_bytes(200, file_path.read_bytes(), f"{content_type}; charset=utf-8")

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/state":
                self._send_json(200, service.state())
            else:
                self._send_static(path)

        def do_POST(self):
            path = urlsplit(self.path).path
            try:
                if path == "/api/orders":
                    self._send_json(201, service.submit_order(self._read_json()))
                elif path == "/api/reset":
                    service.reset()
                    self._send_json(200, service.state())
                else:
                    self._send_json(404, {"error": "Not found"})
            except (TypeError, ValueError) as error:
                self._send_json(400, {"error": str(error)})

        def do_DELETE(self):
            path = urlsplit(self.path).path
            prefix = "/api/orders/"
            if not path.startswith(prefix):
                self._send_json(404, {"error": "Not found"})
                return
            raw_order_id = path[len(prefix):]
            if not raw_order_id.isdigit():
                self._send_json(400, {"error": "Order ID must be a positive whole number"})
                return
            try:
                order_id = service._positive_int(int(raw_order_id), "Order ID")
                cancelled, current_state = service.cancel_order(order_id)
                self._send_json(200, {"cancelled": cancelled, **current_state})
            except ValueError as error:
                self._send_json(400, {"error": str(error)})

        def log_message(self, format_string, *args):
            print(f"[web] {self.address_string()} - {format_string % args}")

    return Handler


def create_server(host="127.0.0.1", port=8000, service=None):
    service = service or TradingEngineService()
    server = ThreadingHTTPServer((host, port), make_handler(service))
    server.daemon_threads = True
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the ChronosMatch local web demo")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    args = parser.parse_args(argv)
    server = create_server(args.host, args.port)
    print(f"ChronosMatch is running at http://{args.host}:{server.server_port}")
    print("Press Ctrl+C to stop the local demo.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping ChronosMatch web demo.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
