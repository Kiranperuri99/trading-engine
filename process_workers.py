import json

from simulation_workers import produce_orders, consume_orders
from worker_config import make_deadline
from worker_queue import open_worker_queue


def producer_process(path, lock, count, seed, timeout, result_path):
    with open_worker_queue(path, lock, make_deadline(timeout)) as queue:
        produced = produce_orders(
            queue, count, seed=seed, timeout=timeout
        )

    with open(result_path, "x", encoding="utf-8") as output:
        json.dump({"orders_produced": produced}, output)


def consumer_process(path, lock, count, timeout, result_path):
    with open_worker_queue(path, lock, make_deadline(timeout)) as queue:
        summary = consume_orders(queue, count, timeout=timeout)

    with open(result_path, "x", encoding="utf-8") as output:
        json.dump(summary, output, allow_nan=False)