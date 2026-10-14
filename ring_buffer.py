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

    def close(self):
        self._storage.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()