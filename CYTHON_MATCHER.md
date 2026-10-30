# Cython matching core

This first Cython milestone ports the price-time matching loop. It keeps the
Python engine as the reference implementation and compares fills, open orders,
and remaining quantities in tests.

The Cython core stores order IDs, prices, and remaining quantities in C structs.
Its best-price search and fill loop run without the Python GIL. Input validation,
updates to the caller's `Order` objects, and Python trade-dictionary creation
still run with the GIL held. Order IDs and quantities are limited to unsigned
64-bit values, matching the binary order format. The core is not yet a drop-in
replacement for all `ChronosMatch` reporting, cancellation, or SQLite methods.

Build and test on Windows PowerShell:

```powershell
python -m pip install -r .\requirements-cython.txt
python .\setup_cython.py build_ext --inplace
python -m unittest test_cython_matcher -v
```

Run the existing Python engine unchanged for reporting, cancellation, and
SQLite features until matching parity is extended to those APIs.

Building a native extension on Windows also requires a working C compiler, such
as the Microsoft C++ Build Tools.
