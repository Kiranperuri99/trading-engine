# Benchmark Procedure

## Before Measuring

1. Use the same computer and Python environment for comparisons.
2. Close unnecessary applications.
3. Record the code version:
   git rev-parse HEAD
4. Run the tests:
   python -m unittest discover -v

## Sequential Baseline

```powershell
python benchmark_simulation.py --count 1000 --seed 42
```

## Concurrent Baseline

```powershell
python benchmark_concurrent.py
```

The concurrent benchmark currently uses 1,000 orders, seed 42,
capacity 16, and a 30-second runner timeout.

## Repeatable Runs

- Run each command once as a warm-up.
- Run each command five more times.
- Keep all five measured results.
- Compare the median elapsed time rather than selecting the fastest run.
- Keep count, seed, queue capacity, and code version consistent.
- Record environment details alongside results.

## What Is Measured

Both benchmarks measure the complete simulation, including setup
and cleanup. The concurrent benchmark also includes process startup.

Orders per second is a throughput measurement.
Average nanoseconds per order is total runtime divided by order count.
It is not an individual order's latency.

## Interpretation

The concurrent version may be slower for small workloads because
process startup, synchronization, and waiting add overhead.

Do not claim a speed improvement without comparable measurements.
Do not claim the project's latency or throughput targets are met
until they have been measured using an appropriate workload.

## Future Measurements

- Per-order latency with explicitly defined start and end points.
- Median, p95, and p99 latency.
- Larger workloads and multiple queue capacities.
- Python versus Cython matching performance.