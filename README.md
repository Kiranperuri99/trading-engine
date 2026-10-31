[![Python tests](https://github.com/Kiranperuri99/trading-engine/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Kiranperuri99/trading-engine/actions/workflows/tests.yml)
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
- Includes an experimental standalone Cython matching core; see [CYTHON_MATCHER.md](CYTHON_MATCHER.md).

## Development Status

The primary engine is a Python prototype using in-memory lists.
Trades execute at the price of the order already waiting in the book.

The Cython matcher is experimental and is not wired into the main simulation.
Simulation and benchmark tools are available; a terminal dashboard is planned.
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
```

## Live engine-call latency dashboard

Display recent per-order engine-call latency as a live terminal graph:

```powershell
python latency_dashboard.py --count 1000 --warmup 100 --seed 42 --window 30 --refresh-every 10
```

The graph shows the most recent samples, rolling minimum, median, p95, and p99,
plus rolling median and p99 separately for BUY and SELL orders. Timing covers
each `ChronosMatch.add_order()` call only; order generation and queue waiting
are excluded. The display refresh runs after each measured call, outside that
call's timed interval. Add `--output latency-live.json` to save the final
summary and measured samples; the command creates a new file and preserves any
existing report.

To mark whether the rolling p99 stays within a latency target, pass a budget in
nanoseconds, for example `--p99-budget-ns 50000`.
When you also save a report with `--output`, its `p99_budget` object records
the limit, measured p99, and whether the budget was met (`null` when no samples
were measured). The `p99_budget_by_side` object reports the same result
separately for BUY and SELL orders.
Add `--fail-on-budget-exceeded` to return exit status 1 when the overall p99
exceeds a configured limit or when no samples were measured. This option
requires at least one p99 budget and is useful in automated checks.
Use `--buy-p99-budget-ns` or `--sell-p99-budget-ns` to override the shared
limit for one side. Side-specific limits can also be used on their own with
`--fail-on-budget-exceeded`.

## Market data and execution summaries

`get_order_book()` returns open buy and sell orders grouped by price. Pass a
positive `depth` value to limit the number of price levels:

```python
book = engine.get_order_book(depth=5)
mid_price = engine.get_mid_price()
spread = engine.get_spread()
traded_units = engine.get_total_traded_quantity()
filled_units = engine.get_filled_quantity(order_id=1)
```

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
See [TESTING.md](TESTING.md) for test commands and verification examples.
## Execution summary

The result includes the trade count, total units traded, volume-weighted average price (`vwap`), and average units per trade (`average_trade_size`). When there are no trades, `vwap` and `average_trade_size` are `None`.
## Recent trade history

Use `get_recent_trades(limit=10)` to retrieve the latest trades. The returned records are copies, so editing them does not change the engine's trade history.

```python
recent_trades = engine.get_recent_trades(limit=5)

## Order status

Use `get_order_status(order_id)` to check an order's state. It returns `OPEN`, `FILLED`, `CANCELLED`, or `UNKNOWN`. A partially filled order stays `OPEN` while it has remaining quantity. Cancelling an order changes its status to `CANCELLED`; its completed trades remain in the trade history.

```python
status = engine.get_order_status(1)
print(status)
To count orders in each state, use `get_order_status_counts()`:

```python
counts = engine.get_order_status_counts()
print(counts)
## Automated tests

GitHub Actions runs the Python test suite when changes are pushed to the `main` branch or a pull request is opened. Open the repository's **Actions** tab on GitHub to see whether the test run passed.
## Order book imbalance

`get_book_imbalance()` compares total open buy quantity with total open sell quantity. The result ranges from `-1.0` (only sell quantity) to `1.0` (only buy quantity). A result of `None` means the book is empty.

```python
imbalance = engine.get_book_imbalance()
print(imbalance)
## Microprice

`get_micro_price()` estimates the price using the quantities at the best bid and best ask. It gives more weight to the side with more quantity. It returns `None` if either side of the order book is empty.

```python
micro_price = engine.get_micro_price()
print(micro_price)
## Concurrent pipeline benchmark

Run the concurrent producer and consumer benchmark:

```powershell
python .\measure_concurrent_pipeline.py --count 1000 --seed 7 --capacity 16 --timeout 30 --output .\concurrent_report.json
## Concurrent benchmark

Run a small concurrent benchmark and print a readable summary:

```powershell
python .\measure_concurrent_pipeline.py --count 10 --seed 7 --capacity 4 --timeout 30 --human
```

Add `--output .\concurrent-report.json` to save the full JSON report as well.

## Saving simulation trades to SQLite

Run the simulator with `--database` to save completed trades in a SQLite file:

```powershell
python .\run_simulation.py --count 100 --seed 7 --database .\trades.db --json
## Viewing saved trades

Show the saved trade summary:

```powershell
python .\trade_report.py --database .\trades.db --json
