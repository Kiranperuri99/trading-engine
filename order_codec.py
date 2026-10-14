from math import isfinite
from struct import Struct

# Little-endian layout:
# Q = order ID: unsigned 8-byte integer
# B = side: unsigned 1-byte integer
# d = price: 8-byte floating-point number
# Q = quantity: unsigned 8-byte integer
ORDER_STRUCT = Struct("<QBdQ")
ORDER_SIZE = ORDER_STRUCT.size

BUY = 1
SELL = 2
def encode_order(order):
    max_uint64 = (1 << 64) - 1

    if type(order.order_id) is not int or not (
        1 <= order.order_id <= max_uint64
    ):
        raise ValueError("Order ID must fit a positive unsigned 64-bit integer")

    if type(order.quantity) is not int or not (
        1 <= order.quantity <= max_uint64
    ):
        raise ValueError("Quantity must fit a positive unsigned 64-bit integer")

    if type(order.price) not in (int, float):
        raise ValueError("Price must be a number")

    try:
        price = float(order.price)
    except OverflowError:
        raise ValueError("Price is too large") from None

    if not isfinite(price) or price <= 0:
        raise ValueError("Price must be finite and greater than zero")

    if not isinstance(order.side, str):
        raise ValueError("Side must be BUY or SELL")

    side = order.side.strip().upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("Side must be BUY or SELL")

    return ORDER_STRUCT.pack(
        order.order_id,
        BUY if side == "BUY" else SELL,
        price,
        order.quantity,
    )