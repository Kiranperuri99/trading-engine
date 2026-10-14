from trading_engine import Order
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
def _validated_order_fields(order):
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

    return (
        order.order_id,
        BUY if side == "BUY" else SELL,
        price,
        order.quantity,
    )
def decode_order(record):
    if len(record) != ORDER_SIZE:
        raise ValueError(f"Order record must be exactly {ORDER_SIZE} bytes")

    return decode_order_from(record)


def decode_order_from(buffer, offset=0):
    if type(offset) is not int or offset < 0:
        raise ValueError("Offset must be a non-negative whole number")

    if offset + ORDER_SIZE > len(buffer):
        raise ValueError("Not enough bytes for an order at this offset")

    order_id, side_code, price, quantity = ORDER_STRUCT.unpack_from(
        buffer, offset
    )

    if side_code not in (BUY, SELL):
        raise ValueError("Invalid binary order side")

    if order_id == 0:
        raise ValueError("Order ID must be positive")

    if quantity == 0:
        raise ValueError("Quantity must be positive")

    if not isfinite(price) or price <= 0:
        raise ValueError("Price must be finite and greater than zero")

    return Order(
        order_id,
        "BUY" if side_code == BUY else "SELL",
        price,
        quantity,
    )
def encode_order(order):
    return ORDER_STRUCT.pack(*_validated_order_fields(order))


def encode_order_into(order, buffer, offset=0):
    if type(offset) is not int or offset < 0:
        raise ValueError("Offset must be a non-negative whole number")

    if offset + ORDER_SIZE > len(buffer):
        raise ValueError("Not enough space for an order at this offset")

    fields = _validated_order_fields(order)
    ORDER_STRUCT.pack_into(buffer, offset, *fields)