from time import perf_counter_ns

from engine_summary import summarize_engine
from latency_stats import summarize_latencies
from market_simulator import generate_orders
from trading_engine import ChronosMatch


def measure_engine_latency(count=1000, seed=42):
    engine = ChronosMatch(verbose=False)
    samples = []

    for order in generate_orders(count, seed):
        start = perf_counter_ns()
        engine.add_order(order)
        elapsed = perf_counter_ns() - start
        samples.append(elapsed)

    return {
        "scope": "ChronosMatch.add_order call",
        "configuration": {
            "count": count,
            "seed": seed,
        },
        "latency": summarize_latencies(samples),
        "summary": summarize_engine(engine, len(samples)),
    }


if __name__ == "__main__":
    result = measure_engine_latency()

    print("ChronosMatch engine-call latency")
    print("Excludes queue waiting and order generation.")

    for name, value in result["latency"].items():
        print(f"{name}: {value}")
        