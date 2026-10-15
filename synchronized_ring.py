class SynchronizedRing:
    """Every user of the same ring must share the same lock."""

    def __init__(self, ring, lock):
        self._ring = ring
        self._lock = lock

    def put(self, order):
        with self._lock:
            self._ring.put(order)

    def get(self):
        with self._lock:
            return self._ring.get()

    def __len__(self):
        with self._lock:
            return len(self._ring)
    def try_put(self, order):
        with self._lock:
            if len(self._ring) == self._ring.capacity:
                return False

            self._ring.put(order)
            return True

    def try_get(self):
        with self._lock:
            if len(self._ring) == 0:
                return None

            return self._ring.get()