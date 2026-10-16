from engine_summary import summarize_engine
from trading_engine import ChronosMatch
from time import sleep

from market_simulator import generate_orders
from worker_config import make_deadline


def produce_orders(queue, count, seed=42, timeout=15):
    deadline = make_deadline(timeout)
    produced = 0

    for order in generate_orders(count, seed):
        while not queue.try_put_before(order, deadline):
            sleep(0.001)

        produced += 1

    return produced
def consume_orders(queue, count, timeout=15):
    if type(count) is not int or not 0 <= count <= (1 << 64) - 1:
        raise ValueError("Count must be a non-negative 64-bit integer")

    deadline = make_deadline(timeout)
    engine = ChronosMatch(verbose=False)
    processed = 0

    while processed < count:
        order = queue.try_get_before(deadline)

        if order is None:
            sleep(0.001)
            continue

        engine.add_order(order)
        processed += 1

    return summarize_engine(engine, processed)
    