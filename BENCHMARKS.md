# Benchmark Procedure

## Before measuring

1. Use the same computer and Python environment for comparisons.
2. Close unnecessary applications.
3. Record the code version with `git rev-parse HEAD`.
4. Run the tests with `python -m unittest discover -v`.

## Sequential baseline

```powershell
python benchmark_simulation.py --count 1000 --seed 42
```

## Concurrent baseline

```powershell
python benchmark_concurrent.py
```

The concurrent benchmark currently uses 1,000 orders, seed 42, capacity 16,
and a 30-second runner timeout.

## Repeatable runs

- Run each command once as a warm-up.
- Run each command five more times and keep all five results.
- Compare the median elapsed time rather than selecting the fastest run.
- Keep count, seed, queue capacity, and code version consistent.
- Record environment details alongside results.

## Interpreting results

Both simulation benchmarks measure the complete run, including setup and
cleanup. The concurrent benchmark also includes process startup. Orders per
second is a throughput measurement. Average nanoseconds per order is total
runtime divided by order count; it is not an individual order's latency.

The concurrent version may be slower for small workloads because process
startup, synchronization, and waiting add overhead. Do not claim a speed
improvement or that a latency target is met without comparable measurements.

## Per-order engine latency

Measure the time spent inside each `ChronosMatch.add_order()` call:

```powershell
python measure_engine_latency.py --count 1000 --seed 42 --json --output latency-results.json
```

Use `--warmup` to process orders before measuring:

```powershell
python measure_engine_latency.py --count 1000 --warmup 100 --seed 42 --json --output latency-warmup-results.json
```

Use `--include-samples` to include each measured latency in the JSON report's
`samples_ns` list. Large sample lists make the report larger:

```powershell
python measure_engine_latency.py --count 1000 --seed 42 --json --include-samples --output latency-samples.json
```

Use `--csv-output` to save one row per measured order, including its order ID,
side, latency in nanoseconds, and UTC timestamp:

```powershell
python measure_engine_latency.py --count 1000 --seed 42 --csv-output engine-latency-samples.csv
```

The CSV and JSON output paths must be new files; existing files are not
overwritten.

The report includes p95, p99, and p99.9 latency in nanoseconds. Percentiles use
the nearest-rank method, which rounds the percentile position up to the next
sample. With 100 samples, p99.9 is the slowest sample, so use a sufficiently
large workload when examining tail latency.

## Latency budgets

Set a global percentile budget with `--p95-budget-ns`, `--p99-budget-ns`, or
`--p99-9-budget-ns`. A BUY or SELL budget overrides the global budget for that
side. Add `--fail-on-budget-exceeded` to return exit code 1 if any configured
budget is exceeded or its percentile cannot be measured.

For example, set a global p99.9 limit and separate limits for BUY and SELL:

```powershell
python measure_engine_latency.py --count 10000 --p99-9-budget-ns 50000 --buy-p99-9-budget-ns 45000 --sell-p99-9-budget-ns 55000 --fail-on-budget-exceeded
```

## Live latency dashboard

Run the terminal dashboard with a rolling window and p99.9 budgets:

```powershell
python latency_dashboard.py --count 1000 --seed 42 --warmup 100 --window 50 --refresh-every 10 --p99-9-budget-ns 50000 --buy-p99-9-budget-ns 45000 --sell-p99-9-budget-ns 55000 --fail-on-budget-exceeded --output latency-dashboard.json
```

The dashboard can also use `--p95-budget-ns`, `--buy-p95-budget-ns`, and
`--sell-p95-budget-ns`, along with the equivalent p99 and p99.9 options.
`--output` saves the final JSON report; `--csv-output`
saves one CSV row per measured order. Both output paths must be new files. The
JSON and CSV paths must also be different from each other. The
JSON report records the rolling `window` and `refresh_every` settings under
`dashboard`. Add `--json` to print the final report to stdout while the live
progress display is sent to stderr.

Use `python latency_dashboard.py --help` to see all available options.

## Further comparisons

For a repeatable Python-versus-Cython matcher comparison, see
[CYTHON_MATCHER.md](CYTHON_MATCHER.md).

Export each measured run from that comparison to CSV with:

```powershell
python benchmark_matchers.py --count 1000 --seed 42 --repeats 5 --warmup 1 --csv-output matcher-timings.csv --output matcher-report.json
```

The text and JSON reports include minimum, median, and maximum elapsed batch
times for each matcher. These values summarize full workload runs; the
benchmark does not measure the latency of individual orders.

The JSON report includes a UTC generation timestamp. The CSV includes that
timestamp alongside the matcher name, run number, elapsed nanoseconds, order
count, per-run orders per second, seed, measured repeat count, warm-up count,
Python version and implementation, operating system and release, machine, and
pointer width. It also records each matcher’s trade count, traded quantity,
and remaining BUY and SELL quantities. Each row also includes the paired-run
speedup ratio, calculated as Python elapsed time divided by Cython elapsed
time for that repeat. Each row therefore keeps its report time, workload
settings, runtime environment, outcome summary, and paired comparison. The
CSV output path must be new; existing files are not overwritten. `--output`
saves the full JSON report, and its path must be new and different from the CSV
path.
