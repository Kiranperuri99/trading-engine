# trading-engine
ChronosMatch is a high-performance trading engine project focused on low-latency order matching, efficient memory management, and zero-copy data processing. It aims to simulate high-frequency trading workflows with fast order execution, bid/ask order books, and optimized trade matching.
## Running ChronosMatch

Open a terminal in the project folder.

Run the sample trading engine:

```powershell
python trading-engine-main.py
```

Run the automated tests:

```powershell
python -m unittest -v test_engine
```

The sample matches 5 units and leaves a buy order with 5 units remaining.

## Current Features

- Validates order IDs, sides, prices, and quantities.
- Rejects duplicate IDs among waiting orders.
- Matches compatible buy and sell orders with partial fills.
- Preserves arrival priority for orders at the same price.
- Records completed trades.
- Supports cancellation of waiting orders.
- Reports best bid, best ask, spread, and pending quantities.
- Calculates total traded quantity.
- Supports quiet mode with `ChronosMatch(verbose=False)`.

## Development Status

This is a Python prototype using in-memory lists.
The current execution price is the matched sell order's price.

Shared-memory IPC, the Cython engine, market simulator, latency
benchmarks, and terminal dashboard are planned.
Performance targets have not yet been verified.