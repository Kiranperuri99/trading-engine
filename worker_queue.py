from contextlib import contextmanager

from ring_buffer import RingBuffer
from synchronized_ring import SynchronizedRing
from worker_config import acquire_before


@contextmanager
def open_worker_queue(path, lock, deadline):
    with acquire_before(lock, deadline):
        ring = RingBuffer.open_existing(path)

    try:
        yield SynchronizedRing(ring, lock)
    finally:
        ring.close()