
# Testing ChronosMatch

Run these commands from the project folder.

## Full test suite

```powershell
python -m unittest discover -v
```

A successful run ends with `OK`. The test count can change as tests are added.

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