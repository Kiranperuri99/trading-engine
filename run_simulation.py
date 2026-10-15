import json
import argparse
from sys import argv
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

def non_negative_count(value):
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Order count must be a whole number"
        ) from None

    if not 0 <= count <= (1 << 64) - 1:
        raise argparse.ArgumentTypeError(
            "Order count must be between 0 and 18446744073709551615"
        )

    return count


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the ChronosMatch sequential simulation."
    )
    parser.add_argument(
        "--count",
        type=non_negative_count,
        default=100,
        help="Number of orders to generate (default: 100)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for repeatable orders (default: 42)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the simulation summary as JSON",
    )
    
    return parser
def main(argv=None):
    args = build_parser().parse_args(argv)
    summary = run_simulation(count=args.count, seed=args.seed)

    if args.json:
        print(json.dumps(summary, indent=2, allow_nan=False))
    else:
        print("ChronosMatch simulation")
        print("Mode: sequential ring-buffer pipeline")

        for name, value in summary.items():
            print(f"{name}: {value}")


if __name__ == "__main__":
    main()