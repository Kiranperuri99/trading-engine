import argparse
import json
from pathlib import Path

from trade_store import SQLiteTradeStore

def positive_order_id(value):
    try:
        order_id = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Order ID must be a positive whole number"
        ) from None

    if order_id <= 0:
        raise argparse.ArgumentTypeError(
            "Order ID must be a positive whole number"
        )

    return order_id
def build_parser():
    parser = argparse.ArgumentParser(
        description="Show a summary of trades saved in SQLite."
    )
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Path to the SQLite trade database",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the summary as JSON",
    )
    parser.add_argument(
        "--order-id",
        type=positive_order_id,
        help="Show trades involving this order ID",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.database.is_file():
        parser.error(f"Database file does not exist: {args.database}")

    with SQLiteTradeStore(args.database) as store:
        summary = store.get_trade_summary()

    if args.json:
        print(json.dumps(summary, indent=2, allow_nan=False))
    else:
        print("Saved trade summary")
        for name, value in summary.items():
            print(f"{name}: {value}")


if __name__ == "__main__":
    main()
