from struct import Struct

from order_codec import ORDER_SIZE

# Header fields: capacity, read position, write position, order count.
HEADER_STRUCT = Struct("<QQQQ")
HEADER_SIZE = HEADER_STRUCT.size


def storage_size(capacity):
    if type(capacity) is not int or capacity <= 0:
        raise ValueError("Capacity must be a positive whole number")

    return HEADER_SIZE + capacity * ORDER_SIZE


def slot_offset(index, capacity):
    storage_size(capacity)

    if type(index) is not int or not 0 <= index < capacity:
        raise ValueError("Slot index is outside the buffer")

    return HEADER_SIZE + index * ORDER_SIZE