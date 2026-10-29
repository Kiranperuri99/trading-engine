import argparse
from html import parser
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
        help="Print the report as JSON",
    )

    order_options = parser.add_mutually_exclusive_group()
    order_options.add_argument(
        "--order-id",
        type=positive_order_id,
        help="Show trades involving this order ID",
    )
    order_options.add_argument(
        "--order-summary",
        type=positive_order_id,
        help="Show a summary for this order ID",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Save the report as JSON to this file",
    )
    return parser
def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.database.is_file():
        parser.error(f"Database file does not exist: {args.database}")

    with SQLiteTradeStore(args.database) as store:
        if args.order_summary is not None:
            report = store.get_trade_summary_for_order(args.order_summary)
        elif args.order_id is not None:
            report = store.get_trades_for_order(args.order_id)
        else:
            report = store.get_trade_summary()

    report_json = json.dumps(report, indent=2, allow_nan=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report_json + "\n", encoding="utf-8")

    if args.json:
        print(report_json)
    elif args.order_summary is not None:
        print(f"Trade summary for order ID {args.order_summary}")
        for name, value in report.items():
            print(f"{name}: {value}")
    elif args.order_id is None:
        print("Saved trade summary")
        for name, value in report.items():
            print(f"{name}: {value}")
    else:
        print(f"Trades involving order ID {args.order_id}")
        for trade in report:
            print(trade)
if __name__ == "__main__":
    main()
