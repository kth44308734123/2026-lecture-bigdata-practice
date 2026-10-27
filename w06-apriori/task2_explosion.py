#!/usr/bin/env python3
"""Week 6 · Task 2 — Lower the threshold until your machine says no.

Textbook §6.1, §6.2.

Support is a knob, and turning it down is how you find the interesting rules.
It is also how you run out of memory, and where that happens is a fact about
your laptop rather than about the algorithm.

    python3 task2_explosion.py --supports 400,200,100,50,25
    python3 task2_explosion.py --supports 12,6            # careful

Lower the threshold until something gives. Write down where and what.
"""
import argparse, json, os, platform, time, tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def machine():
    return {"platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "python": platform.python_version()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--supports", default="400,200,100,50,25")
    p.add_argument("--smoke", action="store_true",
                   help="small correctness run; writes out/smoke/, not submission measurements")
    a = p.parse_args()
    out = os.path.join(OUT, "smoke") if a.smoke else OUT
    os.makedirs(out, exist_ok=True)

    import bench
    from task3_pcy import PlainApriori
    if a.smoke:
        bench.BASKETS, bench.ITEMS, bench.AVG = 300, 100, 8
    baskets = bench.build()

    rows = []
    for support in [int(x) for x in a.supports.split(",")]:
        algo = PlainApriori(support)
        tracemalloc.start()
        t0 = time.perf_counter()
        pairs = algo.run(baskets)
        elapsed = time.perf_counter() - t0
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        row = {"support": support, "frequent_pairs": len(pairs),
               "peak_counters": algo.peak_counters, "seconds": elapsed,
               "peak_bytes": peak_bytes}
        rows.append(row)
        print(f"  support {support:>5}   pairs {len(pairs):>7,}   "
              f"counters {algo.peak_counters:>10,}   "
              f"{elapsed:>7.2f}s   {peak_bytes / 1e6:>8.1f} MB")

    path = os.path.join(out, "explosion.json")
    prior = json.load(open(path)) if os.path.exists(path) else {"runs": []}
    prior["machine"] = machine()
    prior["dataset"] = {"baskets": len(baskets), "items": bench.ITEMS,
                        "average_items": bench.AVG, "seed": bench.SEED,
                        "scope": "smoke" if a.smoke else "assignment"}
    prior["runs"].extend(rows)
    json.dump(prior, open(path, "w"), indent=2)
    print(f"\n  -> {os.path.relpath(path, HERE)}  ({len(prior['runs'])} run(s))")
    print("  Smoke test only; full measurements deferred." if a.smoke else
          "  Keep halving the support until it is unbearable. Record where.")


if __name__ == "__main__":
    main()
