from math import isfinite
from dataclasses import dataclass


@dataclass
class Order:
    order_id: int
    side: str
    price: float
    quantity: int


class ChronosMatch:
    def __init__(self, verbose=True, trade_store=None):
        self.trade_store = trade_store
        self.verbose = verbose
        self.seen_order_ids = set()
        self.cancelled_order_ids = set()
        self.buy_orders = []
        self.sell_orders = []
        self.trades = []
    def add_order(self, order):
        if not isinstance(order, Order):
            raise TypeError("order must be an Order")
        if type(order.order_id) is not int or order.order_id <= 0:
            raise ValueError("Order ID must be a positive integer")
        if order.order_id in self.seen_order_ids:
            raise ValueError("Order ID has already been used")
        
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
            

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")
        order.side = side
        if self.verbose:
            print(f"New order: {order}")

        if side == "BUY":
            self.buy_orders.append(order)
        else:
            self.sell_orders.append(order)

        self.seen_order_ids.add(order.order_id)
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
    def cancel_all_orders(self, side=None):
        if side is None:
            books = (self.buy_orders, self.sell_orders)
        else:
            if not isinstance(side, str):
                raise ValueError("Side must be BUY or SELL")

            side = side.strip().upper()
            if side == "BUY":
                books = (self.buy_orders,)
            elif side == "SELL":
                books = (self.sell_orders,)
            else:
                raise ValueError("Side must be BUY or SELL")

        cancelled_count = sum(len(book) for book in books)
        for book in books:
            self.cancelled_order_ids.update(order.order_id for order in book)
            book.clear()

        return cancelled_count
    def reduce_order_quantity(self, order_id, new_quantity):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")
        if type(new_quantity) is not int or new_quantity <= 0:
            raise ValueError("New quantity must be a positive integer")

        for book in (self.buy_orders, self.sell_orders):
            for order in book:
                if order.order_id == order_id:
                    if new_quantity > order.quantity:
                        raise ValueError(
                            "New quantity cannot exceed remaining quantity"
                        )
                    order.quantity = new_quantity
                    return True

        return False
    def cancel_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive whole number")
        for orders in (self.buy_orders, self.sell_orders):
            for index, order in enumerate(orders):
                if order.order_id == order_id:
                    self.cancelled_order_ids.add(order_id)
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
    def get_best_level(self, side):
        if not isinstance(side, str):
            raise ValueError("Side must be BUY or SELL")

        side = side.strip().upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")

        book = self.get_order_book(depth=1)
        levels = book["bids"] if side == "BUY" else book["asks"]
        return levels[0] if levels else None
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
    def get_book_summary(self):
        def summarize(orders):
            return {
                "order_count": len(orders),
                "total_quantity": sum(order.quantity for order in orders),
            }

        return {
            "BUY": summarize(self.buy_orders),
            "SELL": summarize(self.sell_orders),
        }
    def get_book_imbalance(self):
        quantities = self.pending_quantities()
        buy_quantity = quantities["BUY"]
        sell_quantity = quantities["SELL"]
        total_quantity = buy_quantity + sell_quantity

        if total_quantity == 0:
            return None

        return (buy_quantity - sell_quantity) / total_quantity
    def get_micro_price(self):
        best_bid = self.get_best_level("BUY")
        best_ask = self.get_best_level("SELL")

        if best_bid is None or best_ask is None:
            return None

        bid_price = best_bid["price"]
        ask_price = best_ask["price"]
        bid_quantity = best_bid["quantity"]
        ask_quantity = best_ask["quantity"]

        return bid_price + (ask_price - bid_price) * (
            bid_quantity / (bid_quantity + ask_quantity)
        )
    def get_mid_price(self):
        bid = self.best_bid()
        ask = self.best_ask()

        if bid is None or ask is None:
            return None

        return bid + (ask - bid) / 2
    def get_spread(self):
        return self.spread()
    def get_total_traded_quantity(self):
        return self.total_traded_quantity()
    def get_filled_quantity(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")
        return sum(
            trade["quantity"]
            for trade in self.trades
            if trade["buy_order_id"] == order_id
            or trade["sell_order_id"] == order_id
        )
    def get_execution_summary(self):
        trade_count = len(self.trades)
        total_quantity = self.total_traded_quantity()

        return {
            "trade_count": trade_count,
            "total_quantity": total_quantity,
            "vwap": self.get_vwap(),
            "average_trade_size": (
                total_quantity / trade_count if trade_count else None
            ),
        }
    def get_queue_ahead_quantity(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        for book in (self.buy_orders, self.sell_orders):
            for index, order in enumerate(book):
                if order.order_id == order_id:
                    return sum(
                        earlier.quantity
                        for earlier in book[:index]
                        if earlier.price == order.price
                    )

        return None
    def get_order_status_counts(self):
        open_ids = {
            order.order_id
            for order in self.buy_orders + self.sell_orders
        }
        filled_ids = (
            self.seen_order_ids - open_ids - self.cancelled_order_ids
        )

        return {
            "OPEN": len(open_ids),
            "FILLED": len(filled_ids),
            "CANCELLED": len(self.cancelled_order_ids),
        }
    def get_order_status(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        for order in self.buy_orders + self.sell_orders:
            if order.order_id == order_id:
                return "OPEN"

        if order_id in self.cancelled_order_ids:
            return "CANCELLED"

        if order_id in self.seen_order_ids:
            return "FILLED"

        return "UNKNOWN"
    def get_open_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")

        for side, book in (("BUY", self.buy_orders), ("SELL", self.sell_orders)):
            for order in book:
                if order.order_id == order_id:
                    return {
                        "order_id": order.order_id,
                        "side": side,
                        "price": order.price,
                        "quantity": order.quantity,
                    }

        return None
    def get_remaining_quantity(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")
        for order in self.buy_orders + self.sell_orders:
            if order.order_id == order_id:
                return order.quantity

        return 0
    def get_vwap(self):
        average_price = None
        total_quantity = 0

        for trade in self.trades:
            quantity = trade["quantity"]
            total_quantity += quantity

            if average_price is None:
                average_price = float(trade["price"])
            else:
                weight = quantity / total_quantity
                average_price += (trade["price"] - average_price) * weight

        return average_price
    def get_recent_trades(self, limit=10):
        if type(limit) is not int or limit <= 0:
            raise ValueError("Limit must be a positive integer")

        return [trade.copy() for trade in self.trades[-limit:]]
    def get_trades_for_order(self, order_id):
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")
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
            if self.trade_store:
                self.trade_store.record_trade(self.trades[-1])
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

