## Day 5 progress

- Added latency measurements for individual engine calls.
- Reported latency separately for BUY and SELL orders.
- Added optional warm-up orders and raw latency samples.
- Added a report timestamp and schema version.
- Documented the latency report options.

Validation: `python -m unittest discover -v` — passed.