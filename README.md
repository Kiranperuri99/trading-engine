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
Trades execute at the price of the order already waiting in the book.

Shared-memory IPC, the Cython engine, market simulator, latency
benchmarks, and terminal dashboard are planned.
Performance targets have not yet been verified.
## Simulation

Run the sequential ring-buffer simulation:

```powershell
python run_simulation.py --count 200 --seed 7
```

Print the summary as JSON:

```powershell
python run_simulation.py --count 200 --seed 7 --json
```

Using the same count and seed produces repeatable simulated orders.
The summary includes processed orders, trades, pending quantities,
best bid, best ask, and spread.

## Baseline Benchmark

```powershell
python benchmark_simulation.py --count 1000 --seed 42
```

The timer includes order generation, temporary file setup, queueing,
matching, and cleanup.

- `elapsed_ns`: total duration in nanoseconds.
- `orders_per_second`: processed orders divided by total seconds.
- `average_ns_per_order`: total duration divided by processed orders.

This average is not a measurement of individual order latency.
Results depend on the computer and workload; performance targets
have not yet been verified.

## Run All Tests

```powershell
python -m unittest discover -v
```