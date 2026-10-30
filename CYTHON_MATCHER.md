# Cython matching core

This first Cython milestone ports the price-time matching loop. It keeps the
Python engine as the reference implementation and compares fills, open orders,
and remaining quantities in tests.

The Cython core stores order IDs, prices, and remaining quantities in C structs.
Its best-price search and fill loop run without the Python GIL. Input validation,
updates to the caller's `Order` objects, and Python trade-dictionary creation
still run with the GIL held. Order IDs and quantities are limited to unsigned
64-bit values, matching the binary order format. The core supports
`cancel_order(order_id)` for removing an unfilled order from either side of the
book. Order IDs remain reserved after cancellation, matching the Python engine.
It is not yet a drop-in replacement for all `ChronosMatch` reporting or SQLite
methods.

Build and test on Windows PowerShell:

```powershell
python -m pip install -r .\requirements-cython.txt
python .\setup_cython.py build_ext --inplace
python -m unittest test_cython_matcher -v
```

Use the Python engine for reporting and SQLite features until the Cython core
adds parity for those APIs. The Cython core supports `cancel_order()` for open
orders.

## Compare Python and Cython matching speed

After building the extension, run the same deterministic order stream through
both matching cores:

```powershell
python .\benchmark_matchers.py --count 10000 --seed 42 --repeats 5 --warmup 1 --json
```

The benchmark creates the order stream and engine instances outside the timed
region. It times `add_order()` calls, confirms that trades and remaining books
match, and reports each run plus the median. `cython_speedup_ratio` is the
Python median time divided by the Cython median time; values above 1 indicate
that Cython was faster for that run. Repeat on the same machine and workload,
and do not treat one result as a guaranteed performance target.

Building a native extension on Windows also requires a working C compiler, such
as the Microsoft C++ Build Tools.
