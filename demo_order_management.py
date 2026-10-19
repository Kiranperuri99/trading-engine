from trading_engine import ChronosMatch, Order


def main():
    engine = ChronosMatch(verbose=False)
    engine.add_order(Order(1, "BUY", 100.0, 5))
    engine.add_order(Order(2, "SELL", 100.0, 2))
    print("After partial fill:", engine.get_order_book())

    engine.reduce_order_quantity(1, 1)
    print("After reduction:", engine.get_order_book())

    cancelled = engine.cancel_all_orders()
    print("Orders cancelled:", cancelled)
    print("Final order book:", engine.get_order_book())
    print("Units traded:", engine.total_traded_quantity())


if __name__ == "__main__":
    main()