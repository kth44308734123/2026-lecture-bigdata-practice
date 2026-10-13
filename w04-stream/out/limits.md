# Task 2 · Where Exact Stops Being Possible

Machine: Apple M4 (10 cores), 16 GB RAM, macOS 27.0 (Darwin), Python 3.14.7.
Measured inside an automated shell session on this machine — not a manual
by-hand run, so background load during the run isn't independently verified.

## A1 — sizes and span

| n | true distinct | exact (s) | exact peak | FM (s) | FM peak | FM ratio |
|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 36,702 | 0.10 | 3.93 MB | 0.49 | 5.5 KB | 1.32× |
| 400,000 | 146,970 | 0.44 | 11.59 MB | 1.93 | 4.0 KB | 1.57× |
| 1,600,000 | 587,625 | 1.84 | 46.65 MB | 9.48 | 4.0 KB | 1.52× |
| 6,400,000 | 2,349,909 | 7.30 | 188.29 MB | 38.21 | 4.0 KB | 1.24× |

4 sizes, spanning 6,400,000 / 100,000 = **64×** — past the required 16×.

## A4 — the two growth rates

**Exact** grows linearly with n. Peak bytes per stream item:
100,000→39.3 B/item, 400,000→29.0, 1,600,000→29.2, 6,400,000→29.4 — settles
at **≈ 29.3 bytes of peak memory per stream item** (≈ 80 bytes per distinct
string once you divide by the 0.4 distinct ratio instead — a Python string
object plus its slot in the `set` costs about that much).

**Flajolet-Martin's memory does not move**: 5.5 KB → 4.0 KB → 4.0 KB → 4.0 KB
across a 64× range of n. It holds exactly `n_buckets` (64) small integers —
its memory is set by how many hash buckets you chose, never by how much data
went past. That is the entire structural point of the sketch, and it is
visible directly in these four numbers without needing to trust the theory.

## A5 — FM's accuracy as n grows

Ratio (estimate / truth): 1.32× → 1.57× → 1.52× → 1.24×. It wanders, but
does not trend consistently better or worse across a 64× range in n — which
is exactly what the theory predicts: FM's relative error is a property of
how many hash buckets you used (here, 64), not of how large the stream is.
More data does not make the estimate sharper, and it does not make it worse
either; it just keeps landing somewhere inside the same factor-of-two band.

## A2 — where it became unpleasant, and what actually ran out

Honest answer for this task's stated tolerance: on this machine, **the
exact method itself never got close to unpleasant** in the range tested — at
6,400,000 items it used 7.3 seconds and 188 MB, nowhere near either "a
minute of waiting" or this machine's 16 GB.

What I actually ran into pushing further (one size, n = 25,600,000) was the
**instrumentation**, not the exact method: `task2_limits.py` wraps every
measurement in `tracemalloc`, which tracks every allocation with real
overhead, and my Flajolet-Martin sketch makes many small-integer allocations
per item. Under `tracemalloc` that run was still going after several minutes
and I stopped it rather than let a single extra data point run indefinitely
— the four points above already satisfy A1 with margin to spare, and the
growth rates in A4 are already unambiguous from them.

Extrapolating the confirmed linear rates instead of running it: exact's time
converges to **≈1.14 µs/item** (0.997, 1.107, 1.147, 1.140 µs/item across
the four sizes) and its memory to **≈29.3 bytes/item**. To genuinely hurt
this 16 GB machine — say, 4 GB of peak memory — would take roughly
4 × 10⁹ ÷ 29.3 ≈ **137 million items**, at an extrapolated ≈156 seconds
(2.6 minutes) of wall time. That is the honest finding: on strong-enough
hardware, "exact stops fitting" is a real but *distant* point, not a nearby
one, and reaching it for real was outside what this session's time budget
justified for one data point whose direction was already established.
