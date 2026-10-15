from ring_layout import validate_header
from order_codec import decode_order_from
from order_codec import encode_order_into
from ring_layout import slot_offset
from mapped_storage import MappedStorage
from ring_layout import HEADER_STRUCT, storage_size


class RingBuffer:
    def __init__(self, path, capacity):
        size = storage_size(capacity)

        if capacity > (1 << 64) - 1:
            raise ValueError("Capacity exceeds the header's integer limit")

        self._storage = MappedStorage(path, size)

        try:
            # capacity, read position, write position, order count
            HEADER_STRUCT.pack_into(
                self._storage.buffer, 0, capacity, 0, 0, 0
            )
        except Exception:
            self._storage.close()
            raise

    @property
    def capacity(self):
        return HEADER_STRUCT.unpack_from(self._storage.buffer, 0)[0]

    def __len__(self):
        return HEADER_STRUCT.unpack_from(self._storage.buffer, 0)[3]

    def put(self, order):
        buffer = self._storage.buffer
        capacity, read_pos, write_pos, count = (
            HEADER_STRUCT.unpack_from(buffer, 0)
        )

        if count == capacity:
            raise BufferError("Ring buffer is full")

        encode_order_into(
            order,
            buffer,
            slot_offset(write_pos, capacity),
        )

        next_write = (write_pos + 1) % capacity
        HEADER_STRUCT.pack_into(
            buffer, 0, capacity, read_pos, next_write, count + 1
        )
    def get(self):
        buffer = self._storage.buffer
        capacity, read_pos, write_pos, count = (
            HEADER_STRUCT.unpack_from(buffer, 0)
        )

        if count == 0:
            raise BufferError("Ring buffer is empty")

        order = decode_order_from(
            buffer,
            slot_offset(read_pos, capacity),
        )

        next_read = (read_pos + 1) % capacity
        HEADER_STRUCT.pack_into(
            buffer, 0, capacity, next_read, write_pos, count - 1
        )

        return order
    @classmethod
    def open_existing(cls, path):
        ring = cls.__new__(cls)
        ring._storage = MappedStorage.open_existing(path)

        try:
            validate_header(ring._storage.buffer)
        except Exception:
            ring._storage.close()
            raise

        return ring

    def close(self):
        self._storage.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()