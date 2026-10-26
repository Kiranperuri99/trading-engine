@'
# ChronosMatch Architecture

## Matching engine
`trading_engine.py` contains the `Order` data and `ChronosMatch` engine. The engine validates orders, matches compatible BUY and SELL orders, handles partial fills, and records trade information.

## Order queue
`order_codec.py` encodes and decodes orders. `ring_layout.py` describes the queue header and order slots. `mapped_storage.py` opens the file-backed storage, and `ring_buffer.py` adds and removes orders in arrival order. `synchronized_ring.py` protects shared queue access with a lock.

## Simulation
The worker modules produce and consume queued orders. `run_simulation.py` provides a regular simulation, and `run_concurrent.py` runs the concurrent version.

## Performance tools
The measurement scripts report engine-call latency and concurrent-pipeline throughput. Their results depend on the computer and Python environment.

## Current scope
ChronosMatch is a Python command-line prototype. The code reviewed so far does not include a visual frontend, web API, or SQL database.
'@ | Set-Content .\PROJECT_ARCHITECTURE.md -Encoding utf8