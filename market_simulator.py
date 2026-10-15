import random

from trading_engine import Order


def generate_orders(count, seed=0):
    if type(count) is not int or not 0 <= count <= (1 << 64) - 1:
        raise ValueError("Count must be a non-negative 64-bit integer")

    rng = random.Random(seed)

    for order_id in range(1, count + 1):
        yield Order(
            order_id=order_id,
            side=rng.choice(("BUY", "SELL")),
            price=rng.randint(9900, 10100) / 100,
            quantity=rng.randint(1, 10),
        )