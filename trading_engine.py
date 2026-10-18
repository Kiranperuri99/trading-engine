from math import isfinite
from dataclasses import dataclass


@dataclass
class Order:
    order_id: int
    side: str
    price: float
    quantity: int


class ChronosMatch:
    def __init__(self, verbose=True):
        self.seen_order_ids = set()
        self.seen_order_ids = set()
        self.verbose = verbose
        self.buy_orders = []
        self.sell_orders = []
        self.trades = []

    def add_order(self, order):
        if type(order.order_id) is not int or order.order_id <= 0:
            raise ValueError("Order ID must be a positive integer")
        if order.order_id in self.seen_order_ids:
            raise ValueError("Order ID has already been used")
        self.seen_order_ids.add(order.order_id)
        if type(order.quantity) is not int:
            raise ValueError("Quantity must be a whole number")

        if order.quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

        if type(order.price) not in (int, float):
            raise ValueError("Price must be a number")

        try:
            valid_price = isfinite(order.price) and order.price > 0
        except OverflowError:
            raise ValueError("Price is too large") from None

        if not valid_price:
            raise ValueError("Price must be finite and greater than zero")

        
        if not isinstance(order.side, str):
            raise ValueError("Side must be BUY or SELL")

        side = order.side.strip().upper()
            
        if order.price <= 0:
            raise ValueError("Price must be greater than zero")
        

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")
        for existing in self.buy_orders + self.sell_orders:
            if existing.order_id == order.order_id:
                raise ValueError("Order ID is already active")
        if self.verbose:
            if self.verbose:
                print(f"New order: {order}")

        if side == "BUY":
            self.buy_orders.append(order)
        else:
            self.sell_orders.append(order)

        self.match_orders(incoming_order=order)
    def best_bid(self):
        return max(
            (order.price for order in self.buy_orders),
            default=None,
        )

    def best_ask(self):
        return min(
            (order.price for order in self.sell_orders),
            default=None,
        )
    def spread(self):
        bid = self.best_bid()
        ask = self.best_ask()

        if bid is None or ask is None:
            return None

        return ask - bid
    def cancel_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive whole number")
        for orders in (self.buy_orders, self.sell_orders):
            for index, order in enumerate(orders):
                if order.order_id == order_id:
                    del orders[index]
                    return True

        return False
    def total_traded_quantity(self):
        return sum(trade["quantity"] for trade in self.trades)
    def pending_quantities(self):
        return {
            "BUY": sum(order.quantity for order in self.buy_orders),
            "SELL": sum(order.quantity for order in self.sell_orders),
        }
    def get_order_book(self, depth=None):
        if depth is not None and (type(depth) is not int or depth <= 0):
            raise ValueError("Depth must be a positive integer")

        def levels(orders, highest_first):
            totals = {}
            for order in orders:
                totals[order.price] = totals.get(order.price, 0) + order.quantity

            prices = sorted(totals, reverse=highest_first)
            if depth is not None:
                prices = prices[:depth]

            return [
                {"price": price, "quantity": totals[price]}
                for price in prices
            ]

        return {
            "bids": levels(self.buy_orders, highest_first=True),
            "asks": levels(self.sell_orders, highest_first=False),
        }
    def get_mid_price(self):
        if not self.buy_orders or not self.sell_orders:
            return None

        best_bid = max(self.buy_orders, key=lambda order: order.price).price
        best_ask = min(self.sell_orders, key=lambda order: order.price).price

        return (best_bid + best_ask) / 2
    def get_spread(self):
        if not self.buy_orders or not self.sell_orders:
            return None

        best_bid = max(self.buy_orders, key=lambda order: order.price).price
        best_ask = min(self.sell_orders, key=lambda order: order.price).price

        return best_ask - best_bid
    def get_total_traded_quantity(self):
        return sum(trade["quantity"] for trade in self.trades)
    def get_filled_quantity(self, order_id):
        return sum(
            trade["quantity"]
            for trade in self.trades
            if trade["buy_order_id"] == order_id
            or trade["sell_order_id"] == order_id
        )
    def get_remaining_quantity(self, order_id):
        for order in self.buy_orders + self.sell_orders:
            if order.order_id == order_id:
                return order.quantity

        return 0
    def get_vwap(self):
        total_quantity = self.get_total_traded_quantity()
        if total_quantity == 0:
            return None

        total_value = sum(
            trade["price"] * trade["quantity"]
            for trade in self.trades
        )
        return total_value / total_quantity
    def get_trades_for_order(self, order_id):
        return [
            trade.copy()
            for trade in self.trades
            if trade["buy_order_id"] == order_id
            or trade["sell_order_id"] == order_id
        ]
    def match_orders(self, incoming_order=None):
        while self.buy_orders and self.sell_orders:
            buy = max(self.buy_orders, key=lambda order: order.price)
            sell = min(self.sell_orders, key=lambda order: order.price)

            if buy.price < sell.price:
                break
            quantity = min(buy.quantity, sell.quantity)
            trade_price = (
                buy.price if sell is incoming_order else sell.price
            )
            self.trades.append({
                "buy_order_id": buy.order_id,
                "sell_order_id": sell.order_id,
                "price": trade_price,
                "quantity": quantity,
            })
            if self.verbose:
                print(
                f"MATCHED: {quantity} units at "
                f"price {trade_price}"
            )

            buy.quantity -= quantity
            sell.quantity -= quantity

            if buy.quantity == 0:
                self.buy_orders.remove(buy)

            if sell.quantity == 0:
                self.sell_orders.remove(sell)

if __name__ == "__main__":
    engine = ChronosMatch()

    engine.add_order(Order(1, "BUY", 101.0, 10))
    engine.add_order(Order(2, "SELL", 100.0, 5))

