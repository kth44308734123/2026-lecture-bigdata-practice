#!/usr/bin/env python3
"""Week 4 · Task 1 — Answer questions about a stream you cannot store.

Textbook §4.3 (sampling), §4.4 (Bloom filter), §4.5 (Flajolet-Martin).

The premise of the whole chapter: the stream is longer than your memory, it
goes past once, and you still have to answer. Every method here trades an exact
answer for a bounded amount of space, and the job is to know exactly what you
traded.

You build three, and the harness checks each against the truth it is
approximating.

    python3 task1_sketches.py --verify
"""
import argparse, hashlib, math, random


class BloomFilter:
    """Membership, with one-sided error.

    A Bloom filter never says "no" about something you inserted. It sometimes
    says "yes" about something you did not. That asymmetry is the entire design
    and it is why it is useful for "have I seen this before" and useless for
    "is this definitely in the set".

    `m` bits, `k` hash functions.
    """

    def __init__(self, m, k, seed=246):
        self.m = m
        self.k = k
        self.seed = seed
        self.bits = bytearray((m + 7) // 8)

    def _positions(self, item):
        # k separately salted digests give deterministic bit positions.
        base = str(item).encode()
        for i in range(self.k):
            d = hashlib.blake2b(base, digest_size=8,
                                 key=f"{self.seed}-{i}".encode()).digest()
            yield int.from_bytes(d, "big") % self.m

    def add(self, item):
        for pos in self._positions(item):
            self.bits[pos >> 3] |= 1 << (pos & 7)

    def __contains__(self, item):
        # Never a false negative: every bit an insert set stays set, so an
        # item that was added always finds all k of its bits still 1. The
        # only way to answer "no" here is to see an unset bit, which can only
        # happen for something that never set it.
        return all(self.bits[pos >> 3] & (1 << (pos & 7))
                   for pos in self._positions(item))

    def expected_fp_rate(self, n_inserted):
        """The textbook's predicted false-positive rate after n insertions.

        §4.4.2 derives it. Return the number, do not measure it - the harness
        measures separately and compares the two.
        """
        return (1 - math.exp(-self.k * n_inserted / self.m)) ** self.k


def flajolet_martin(stream, n_hashes=64, seed=246):
    """Estimate how many DISTINCT items went past, in almost no memory.

    §4.5. Hash each item, count trailing zeros in the hash, keep the maximum.
    A maximum of R suggests about 2^R distinct items, because seeing R trailing
    zeros is a 1-in-2^R event.

    One hash gives an estimate with enormous variance, so you use many and
    combine them. How you combine them matters a great deal:

      * averaging 2^R directly is dominated by whichever hash got lucky - the
        values are exponential, so one outlier swamps the rest
      * the median is robust but can only ever be a power of two
      * §4.5.3 suggests grouping, and combining twice

    The harness accepts anything **within a factor of two** of the truth. That is
    not a generous tolerance, it is an honest one: this method really is that
    crude, and HyperLogLog exists because of it. Getting inside a factor of two
    reliably is the requirement; getting closer than that is not expected here.

    Return your estimate as a float.

    Implementation note: this hashes each item **once**, not `n_hashes`
    times. §4.5.3's "grouping" is built by using part of that single hash to
    route the item into one of `n_hashes` buckets (stochastic averaging,
    the same trick behind LogLog/HyperLogLog) and the rest of it for the
    trailing-zero count in that bucket. An earlier version of this function
    computed a genuinely separate hash per item *per* bucket - correct, but
    O(n_hashes) Python-level work per stream element, which made Task 2's
    multi-million-item streams unworkably slow. One hash per item, routed
    once, gives the same set of independent-ish R-estimates for O(1) work
    per item.
    """
    if n_hashes <= 0:
        raise ValueError("n_hashes must be positive")
    n_buckets = n_hashes
    route_bits = (n_buckets - 1).bit_length()
    n_buckets = 1 << route_bits  # round up to a power of two for a clean mask
    route_mask = n_buckets - 1
    max_trailing = [0] * n_buckets
    key = str(seed).encode()
    seen = False

    for item in stream:
        seen = True
        h = int.from_bytes(
            hashlib.blake2b(str(item).encode(), digest_size=8, key=key).digest(),
            "big")
        bucket = h & route_mask       # low bits: which of the n_buckets substreams
        rest = h >> route_bits        # remaining bits: this substream's trailing zeros
        tz = (64 - route_bits) if rest == 0 else (rest & -rest).bit_length() - 1
        if tz > max_trailing[bucket]:
            max_trailing[bucket] = tz

    # Each bucket only ever saw about 1/n_buckets of the distinct items (the
    # routing hash partitions them uniformly), so each bucket's own R
    # estimates roughly distinct/n_buckets, and 2^(mean R) undoes that
    # exponent-of-a-count relationship. §4.5.3: group buckets, average R
    # *within* a group before exponentiating (averaging exponents, not
    # already-exponential 2^R, keeps one lucky bucket's outlier R from
    # dragging a linear sum up by a factor of 2^(that outlier) - tried
    # averaging 2^R directly here first and it measured 3x worse), then take
    # the *median* across groups to tame one unlucky group. Multiplying the
    # combined per-bucket estimate back up by n_buckets undoes the partition.
    if not seen:
        return 0.0
    n_groups = max(1, int(math.sqrt(n_buckets)))
    group_size = max(1, n_buckets // n_groups)
    group_estimates = []
    for g in range(0, n_buckets, group_size):
        chunk = max_trailing[g:g + group_size]
        group_estimates.append(2 ** (sum(chunk) / len(chunk)))

    group_estimates.sort()
    mid = len(group_estimates) // 2
    if len(group_estimates) % 2:
        per_bucket = group_estimates[mid]
    else:
        per_bucket = (group_estimates[mid - 1] + group_estimates[mid]) / 2
    return per_bucket * n_buckets


def reservoir_sample(stream, k, seed=246):
    """Keep k items uniformly at random from a stream of unknown length.

    §4.3. Every item that went past must end up with the same probability k/n
    of being in your sample, and you only ever hold k of them.

    Return a list of k items (or fewer if the stream was shorter).
    """
    rng = random.Random(seed)
    reservoir = []
    for i, item in enumerate(stream):  # i is 0-based; i+1 items seen so far
        if i < k:
            reservoir.append(item)
        else:
            j = rng.randrange(0, i + 1)
            if j < k:
                reservoir[j] = item
    return reservoir


# ------------------------------------------------------------------- harness
def verify():
    fails = 0
    rng = random.Random(246)

    def check(label, ok, detail=""):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<46} {detail}")
        fails += not ok

    # --- Bloom: no false negatives, ever
    try:
        bf = BloomFilter(m=8192, k=5)
    except NotImplementedError:
        print("  BloomFilter is still a stub"); return 1
    inserted = [f"item-{i}" for i in range(800)]
    for x in inserted:
        bf.add(x)
    check("no false negatives", all(x in bf for x in inserted))

    absent = [f"other-{i}" for i in range(20_000)]
    fp = sum(1 for x in absent if x in bf) / len(absent)
    predicted = bf.expected_fp_rate(len(inserted))
    close = abs(fp - predicted) < max(0.02, predicted * 0.5)
    check("measured false-positive rate matches theory", close,
          f"measured {fp:.3%}, predicted {predicted:.3%}")

    # --- Flajolet-Martin: a factor of two is what this method gives you
    try:
        distinct = 20_000
        stream = [f"k{rng.randrange(distinct)}" for _ in range(120_000)]
        est = flajolet_martin(stream)
    except NotImplementedError:
        print("  flajolet_martin is still a stub"); return 1
    true_distinct = len(set(stream))
    ratio = est / true_distinct
    check("distinct estimate within a factor of 2", 0.5 <= ratio <= 2.0,
          f"estimated {est:,.0f}, true {true_distinct:,} ({ratio:.2f}x)")

    # --- Reservoir: uniform over many trials
    try:
        counts = [0] * 20
        trials = 4000
        for t in range(trials):
            s = reservoir_sample(range(20), 5, seed=t)
            for i in s:
                counts[i] += 1
    except NotImplementedError:
        print("  reservoir_sample is still a stub"); return 1
    expected = trials * 5 / 20
    spread = (max(counts) - min(counts)) / expected
    check("reservoir is uniform across items", spread < 0.15,
          f"spread {spread:.1%} around {expected:.0f}")

    print(f"\n  {'all ok' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
