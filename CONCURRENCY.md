# Ring Buffer Concurrency

## Shared Lock Rule

Every process accessing the same ring buffer must use the same
multiprocessing lock.

Create the lock in the parent process:

```python
context = multiprocessing.get_context("spawn")
lock = context.Lock()
```

Pass that lock to each worker through its process arguments.
Creating a separate lock inside each worker does not protect the queue.

## Opening an Existing Queue

Opening validates the queue header, so acquire the shared lock first:

```python
with lock:
    ring = RingBuffer.open_existing(path)

with ring:
    queue = SynchronizedRing(ring, lock)
    # Use queue operations here.
```

Create the ring file before starting workers. Each worker opens its own
mapping of that same file.

## Queue Operations

- put(order): inserts an order; raises BufferError when full.
- get(): returns the oldest order; raises BufferError when empty.
- try_put(order): returns False when full, otherwise inserts and returns True.
- try_get(): returns None when empty, otherwise removes and returns an order.
- len(queue): returns the count observed while holding the lock.

All these operations wait to acquire the shared lock.
The try methods avoid exceptions for full or empty states; they do not
provide a non-blocking lock acquisition.

Do not wrap these methods in another acquisition of the same
non-reentrant lock.

## Important Limits

- Do not mix synchronized operations with unprotected RingBuffer calls
  while workers are running.
- Checking len(queue) and then calling get() is not one atomic operation.
  Another consumer may remove the order between those calls.
  Use try_get() when an empty queue is expected.
- mmap.flush() is not a replacement for synchronization.
- This implementation is lock-based, not lock-free.
- A worker crash while holding the lock can block other workers.
- The queue does not provide transactional crash recovery.
- Direct buffer encoding avoids a temporary encoded byte string,
  but decoding still creates Python objects.