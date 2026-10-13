from math import isfinite
from dataclasses import dataclass


@dataclass
class Order:
    order_id: int
    side: str
    price: float
    quantity: int


class ChronosMatch:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        self.trades = []

    def add_order(self, order):
        if type(order.order_id) is not int or order.order_id <= 0:
            raise ValueError("Order ID must be a positive whole number")
        if type(order.quantity) is not int:
            raise ValueError("Quantity must be a whole number")

        if order.quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

        if type(order.price) not in (int, float):
            raise ValueError("Price must be a number")

        if not isfinite(order.price) or order.price <= 0:
            raise ValueError("Price must be finite and greater than zero")

        
        if not isinstance(order.side, str):
            raise ValueError("Side must be BUY or SELL")

        side = order.side.strip().upper()
            
        if order.price <= 0:
            raise ValueError("Price must be greater than zero")
        

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")

        print(f"New order: {order}")

        if side == "BUY":
            self.buy_orders.append(order)
        else:
            self.sell_orders.append(order)

        self.match_orders()
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
        for orders in (self.buy_orders, self.sell_orders):
            for index, order in enumerate(orders):
                if order.order_id == order_id:
                    del orders[index]
                    return True

        return False
    def match_orders(self):
        while self.buy_orders and self.sell_orders:
            buy = max(self.buy_orders, key=lambda order: order.price)
            sell = min(self.sell_orders, key=lambda order: order.price)

            if buy.price < sell.price:
                break

            quantity = min(buy.quantity, sell.quantity)
            self.trades.append({
                "buy_order_id": buy.order_id,
                "sell_order_id": sell.order_id,
                "price": sell.price,
                "quantity": quantity,
            })
            print(
                f"MATCHED: {quantity} units at "
                f"price {sell.price}"
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

