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
