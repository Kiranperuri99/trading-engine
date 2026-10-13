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

    def match_orders(self):
        while self.buy_orders and self.sell_orders:
            buy = max(self.buy_orders, key=lambda order: order.price)
            sell = min(self.sell_orders, key=lambda order: order.price)

            if buy.price < sell.price:
                break

            quantity = min(buy.quantity, sell.quantity)
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

