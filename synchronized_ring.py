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