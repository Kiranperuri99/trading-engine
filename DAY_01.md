# Day 1 — ChronosMatch
Date: 2026-10-13

## Completed
- Connected the local repository to GitHub.
- Added Git ignore rules.
- Built and extended a basic Python order-matching prototype.
- Added validation for order IDs, quantities, prices, and sides.
- Prevented duplicate active order IDs.
- Recorded completed trades and total traded quantity.
- Added best bid, best ask, spread, and pending quantities.
- Added order cancellation with ID validation.
- Added FIFO matching tests and quiet mode.
- Documented how to run the engine and tests.

## Verification
Run the test suite:
python -m unittest -v test_engine

Expected test count: 26.

## Current Limitations
- Orders are stored in Python lists.
- Trade execution currently uses the sell order's price.
- Shared-memory IPC and Cython are not implemented.
- Latency and throughput targets are not yet measured.

## Day 2 Plan
1. Review the prototype and its matching rules.
2. Replace the legacy test-module loader with a normal import.
3. Define a fixed-size binary order format.
4. Implement and test order encoding and decoding.
5. Start the memory-mapped ring buffer.