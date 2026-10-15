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
def validate_header(buffer):
    if len(buffer) < HEADER_SIZE:
        raise ValueError("Buffer is too small for the ring header")

    capacity, read_pos, write_pos, count = HEADER_STRUCT.unpack_from(
        buffer, 0
    )

    if capacity == 0:
        raise ValueError("Ring capacity must be positive")

    if len(buffer) != storage_size(capacity):
        raise ValueError("Buffer size does not match ring capacity")

    if read_pos >= capacity or write_pos >= capacity:
        raise ValueError("Ring position is outside its capacity")

    if count > capacity:
        raise ValueError("Order count exceeds ring capacity")

    if write_pos != (read_pos + count) % capacity:
        raise ValueError("Ring positions do not match the order count")

    return capacity, read_pos, write_pos, count