# ChronosMatch architecture

ChronosMatch is a local order-matching simulator with a browser demo. It does
not fetch live market prices, connect to an exchange or broker, or place real
trades.

## Main components

| Area | Files | Purpose |
| --- | --- | --- |
| Matching engine | `trading_engine.py` | Validates orders and maintains price-time-priority buy and sell books, matches orders, supports partial fills and cancellations, and reports trades and book statistics. |
| Browser demo | `web_app.py`, `web/index.html` | Serves the local front end and connects its order form to the Python engine through a small JSON API. Each supported ticker has a separate in-memory engine. Prices and chart data are fixed illustrative snapshots. |
| Sequential simulation | `market_simulator.py`, `run_simulation.py`, `ring_buffer.py` | Generates repeatable sample orders and processes them through the engine using a temporary ring buffer. |
| Concurrent pipeline | `run_concurrent.py`, `worker_queue.py`, `worker_config.py`, `process_workers.py`, `simulation_workers.py`, `ring_layout.py`, `mapped_storage.py`, `synchronized_ring.py` | Moves simulated orders through a file-backed ring buffer between worker processes and summarizes the completed run. |
| Trade persistence | `trade_store.py`, `trade_report.py` | Optionally writes completed simulation trades to SQLite and reads them back for reports. The browser demo itself keeps its books in memory. |
| Performance tools | `benchmark_*.py`, `measure_engine_latency.py`, `measure_concurrent_pipeline.py`, `latency_stats.py`, `latency_dashboard.py` | Measures simulation throughput, matcher parity, and engine-call or pipeline latency. Results depend on the machine, Python build, and workload. |
| Experimental matcher | `cython_matcher.pyx`, `setup_cython.py` | Builds a standalone Cython matcher for parity and benchmark experiments. It is not used by the main Python simulation or browser demo. |

## Typical flow

1. The simulator or browser submits a validated order.
2. `ChronosMatch` checks the order against the opposite side of the book.
3. Crossing orders trade at the resting order's price; any unfilled quantity
   remains open in the book.
4. Callers can inspect open orders, best bid and ask, spread, order status, and
   trade history. The simulation can optionally persist trades to SQLite.

## Run and verify

From the repository root, run the full test suite:

```powershell
python -m unittest discover -q
```

Run the local browser demo with `python .\web_app.py`, then open
<http://127.0.0.1:8000>. Use `Ctrl+C` in the terminal to stop the server.

Run a repeatable command-line simulation with
`python .\run_simulation.py --count 100 --seed 7 --json`.

For Windows-specific setup and fuller examples, see [README.md](README.md),
[WEB_DEMO.md](WEB_DEMO.md), [TESTING.md](TESTING.md),
[CONCURRENCY.md](CONCURRENCY.md), [BENCHMARKS.md](BENCHMARKS.md), and
[CYTHON_MATCHER.md](CYTHON_MATCHER.md).

## Scope and limits

This repository demonstrates matching and simulation. The browser's ticker,
prices, and chart are sample data; balances and holdings are not connected to
the matching engine. Restarting the local server resets its in-memory books.
Performance numbers are measurements from a particular environment, not a
guaranteed latency or throughput target.
