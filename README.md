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
## Concurrent Simulation

Run the producer and matching consumer in separate processes:

```powershell
python run_concurrent.py --count 200 --seed 7 --capacity 4 --timeout 30
```

Options:
- `--count`: number of orders to generate.
- `--seed`: seed for repeatable simulated orders.
- `--capacity`: number of order slots in the shared ring buffer.
- `--timeout`: overall runner time limit in seconds, including startup.

Print the summary as JSON:

```powershell
python run_concurrent.py --count 200 --seed 7 --capacity 4 --json
```

The workers share one multiprocessing lock. The parent detects worker
failures and terminates remaining workers if the run fails or times out.

If a valid workload times out on a slow computer, try a smaller count
or a larger timeout. If it still fails, inspect the traceback.

## Concurrent Baseline Benchmark

```powershell
python benchmark_concurrent.py
```

The benchmark currently defaults to 1,000 orders, seed 42,
capacity 16, and a 30-second runner timeout.

Results include:
- Runtime environment details.
- Workload configuration.
- Total elapsed time.
- Orders processed per second.
- Average total time per processed order.

Timing includes setup, process startup, processing, and cleanup.
It does not measure individual order latency.

## Expected Test Output

```powershell
python -m unittest discover -v
```

One failure-handling test deliberately crashes a child worker.
Its traceback may appear even when the suite passes.
Check the final suite result: it must say `OK`.
## Measure engine-call latency

Run this command from the project folder:

```powershell
python measure_engine_latency.py --count 1000 --warmup 100 --seed 42 --json --output latency-report.json
## Market data and execution summaries

`get_order_book()` returns open buy and sell orders grouped by price. Pass a
positive `depth` value to limit the number of price levels:

```python
book = engine.get_order_book(depth=5)
mid_price = engine.get_mid_price()
spread = engine.get_spread()
traded_units = engine.get_total_traded_quantity()
filled_units = engine.get_filled_quantity(order_id=1)
## Cancelling all open orders

Use `cancel_all_orders()` to cancel every currently open buy and sell order:

```python
cancelled_count = engine.cancel_all_orders()
print(f"Cancelled {cancelled_count} open orders")
```

The returned count is the number of orders cancelled, not the number of units.
Calling this method on an empty order book returns `0`.

Trade history remains available after cancellation. Previously accepted order
IDs stay reserved and cannot be reused, including IDs of cancelled orders.
Pass `side="BUY"` or `side="SELL"` to `cancel_all_orders()` to cancel
only that side. Omitting `side` cancels both sides. An invalid side
raises `ValueError` before any orders are cancelled.
Use `reduce_order_quantity(order_id, new_quantity)` to lower an open
order's remaining quantity while preserving its queue position. It
returns `True` for an updated order or `False` for an unknown order.
Invalid quantities and increases raise `ValueError`. Use cancellation
to remove the entire remaining quantity.
Run `python demo_order_management.py` to see a partial fill, a quantity
reduction, and bulk cancellation in one example.
Run `python show_daily_progress.py` to list and count today's local
commits on the current branch. Check GitHub after pushing to confirm
the commits reached the remote repository.
`get_open_order(order_id)` returns a separate dictionary containing an
open order's ID, side, price, and remaining quantity. It returns `None`
for a filled, cancelled, or unknown order. Invalid IDs raise `ValueError`.