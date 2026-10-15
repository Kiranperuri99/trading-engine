import tempfile
from pathlib import Path

from market_simulator import generate_orders
from ring_buffer import RingBuffer
from trading_engine import ChronosMatch


def run_simulation(count=100, seed=42):
    engine = ChronosMatch(verbose=False)
    processed = 0

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "ring.bin"

        with RingBuffer(path, 16) as ring:
            for order in generate_orders(count, seed):
                ring.put(order)

                if len(ring) == ring.capacity:
                    while len(ring):
                        engine.add_order(ring.get())
                        processed += 1

            while len(ring):
                engine.add_order(ring.get())
                processed += 1

    pending = engine.pending_quantities()

    return {
        "orders_processed": processed,
        "trade_count": len(engine.trades),
        "traded_quantity": engine.total_traded_quantity(),
        "pending_buy_quantity": pending["BUY"],
        "pending_sell_quantity": pending["SELL"],
        "best_bid": engine.best_bid(),
        "best_ask": engine.best_ask(),
        "spread": engine.spread(),
    }


if __name__ == "__main__":
    summary = run_simulation()

    print("ChronosMatch simulation")
    print("Mode: sequential ring-buffer pipeline")

    for name, value in summary.items():
        print(f"{name}: {value}")