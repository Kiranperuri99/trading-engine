
# Testing ChronosMatch

Run these commands from the project folder.

## Full test suite

```powershell
python -m unittest discover -v
```

A successful run ends with `OK`. The test count can change as tests are added.

## Optional Cython matcher tests

The Python test suite does not require the native extension. The Cython parity
tests and Python-versus-Cython benchmark require it to be built first:

```powershell
python -m pip install -r .\requirements-cython.txt
python .\setup_cython.py build_ext --inplace --force
python -m unittest test_cython_matcher -v
```

On Windows, run the build from the project folder in a Visual Studio Developer
Command Prompt that matches the Python architecture. For 64-bit Python, use an
x64 developer environment. Rebuild after changing `cython_matcher.pyx`, then
run `python -m unittest discover -v` to check the complete project.

## Focused engine tests

```powershell
python -m unittest test_engine -v
```

These cover validation, matching, order management, market data,
and execution reports.

## Repeatable order-flow test

```powershell
python -m unittest test_engine_invariants -v
```

This submits 200 orders using random seed 42. After each order, it checks:

- Submitted quantities equal traded quantities plus remaining quantities.
- Open orders have positive quantities.
- Remaining buy and sell prices do not cross.

## Order-management example

```powershell
python demo_order_management.py
```

The example demonstrates a partial fill, quantity reduction, and cancellation.
It should finish with an empty order book and two units traded.
## GitHub Actions

The workflow in `.github/workflows/python-tests.yml` runs after pushes to `main` and when a pull request is opened. It checks Python syntax and runs the unit tests across the configured Python versions and operating systems. You can also start it from the repository's **Actions** tab.
## Final review verification

Run the full suite from the project folder and confirm the final output is `OK`:

```powershell
python -m unittest discover -v