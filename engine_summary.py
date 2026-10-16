def summarize_engine(engine, processed):
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