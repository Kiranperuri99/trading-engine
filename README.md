[![Python tests](https://github.com/Kiranperuri99/trading-engine/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Kiranperuri99/trading-engine/actions/workflows/tests.yml)

# ChronosMatch

ChronosMatch is a Python order-matching simulator with a local browser demo.
It demonstrates limit-order matching, price-time priority, partial fills,
cancellation, simulations, and performance measurement. The browser demo uses
fixed sample market data; it does not connect to a broker or exchange or place
real orders.

## Run the browser demo

Open PowerShell in the repository folder and run:

```powershell
python .\web_app.py
```

Keep the terminal open and visit <http://127.0.0.1:8000>. The watchlist,
scrolling ticker, chart, buy/sell ticket, order book, and trade activity run
against local Python matching engines. Each displayed symbol has an independent
in-memory order book. The sample prices and chart are illustrative, not live.
Press `Ctrl+C` in PowerShell to stop the server.

The original project entry point also launches the same demo:
`python .\trading-engine-main.py`.

If port 8000 is already in use, start on another local port:

```powershell
python .\web_app.py --port 8080
```

Then open <http://127.0.0.1:8080>.

## Run a simulation

Run 100 repeatable simulated orders and print a summary:

```powershell
python .\run_simulation.py --count 100 --seed 7
```

Print the same summary as JSON:

```powershell
python .\run_simulation.py --count 100 --seed 7 --json
```

Run the producer and matching consumer in separate processes:

```powershell
python .\run_concurrent.py --count 100 --seed 7 --capacity 16 --timeout 30 --json
```

The seed makes generated orders repeatable. These commands simulate orders;
they do not send orders to a real market.

## Run tests

Run the complete test suite from the repository root:

```powershell
python -m unittest discover -q
```

Run just the matching-engine and browser-service tests:

```powershell
python -m unittest -v test_engine test_web_app
```

The full suite covers matching rules and invariants, order encoding, ring
buffers, worker pipelines, SQLite persistence and reports, latency tools,
benchmarks, and the browser service API.

## What the engine does

- Validates order IDs, side, price, and quantity.
- Matches crossing BUY and SELL limit orders, including partial fills.
- Preserves price-time priority for resting orders.
- Supports cancellation and remaining-quantity reduction.
- Reports best bid and ask, spread, order status, open quantities, and trades.
- Optionally persists completed simulation trades to SQLite.

Trades execute at the resting order's price. The browser demo starts with
illustrative sample orders, keeps each symbol's book in memory, and resets the
books when the server restarts. It does not implement real cash balances,
holdings, authentication, or live market data.

## Optional performance tools

Measure one run of the Python and Cython matchers and check output parity:

```powershell
python .\benchmark_matchers.py --count 500 --seed 42 --repeats 2 --warmup 1 --json
```

The Cython extension must be built first for Cython measurements. See
[CYTHON_MATCHER.md](CYTHON_MATCHER.md). The Cython matcher is experimental and
is not used by the main simulation or web demo.

Measure per-order engine-call latency:

```powershell
python .\measure_engine_latency.py --count 1000 --warmup 100 --seed 42 --json
```

View a live terminal latency dashboard:

```powershell
python .\latency_dashboard.py --count 1000 --warmup 100 --seed 42
```

Timing depends on the computer, Python build, and workload. A benchmark result
is a measurement from that run, not a guaranteed performance target.

## Save and report trades

Save completed simulation trades to a local SQLite database:

```powershell
python .\run_simulation.py --count 100 --seed 7 --database .\trades.db --json
python .\trade_report.py --database .\trades.db --json
```

The `trades.db` file is generated locally and can be deleted to remove that
simulation's saved trades.

## Project guides

- [Project architecture](PROJECT_ARCHITECTURE.md)
- [Browser demo controls and behavior](WEB_DEMO.md)
- [Test and verification guide](TESTING.md)
- [Concurrent pipeline](CONCURRENCY.md)
- [Benchmarking](BENCHMARKS.md)
- [Cython matcher](CYTHON_MATCHER.md)
