#!/usr/bin/env python3
"""Week 6 · Task 3 — Make pass two fit.

Textbook §6.3 (PCY), §6.3.2 - §6.3.4.

`PlainApriori` does what Task 1 asked: use pass one to drop infrequent items,
then count every pair of surviving items. That is already much better than
counting all pairs. It is still not enough, because the surviving items are the
common ones, and the common ones appear together constantly.

The harness measures **the peak number of pair counters you held**, because
that is the thing that decides whether the algorithm runs at all. §6.3 is about
spending pass one's spare memory to shrink it.

    python3 bench.py
    python3 bench.py --yours

Correctness first: you must find exactly the same frequent pairs. Finding fewer
is not an optimisation.
"""
from collections import Counter
from array import array
from itertools import combinations


class PlainApriori:
    """Pass one drops infrequent items. Pass two counts every surviving pair."""

    def __init__(self, support):
        self.support = support
        self.peak_counters = 0

    def run(self, baskets):
        counts = Counter()
        for basket in baskets:
            counts.update(basket)
        frequent = {i for i, c in counts.items() if c >= self.support}

        pair_counts = Counter()
        for basket in baskets:
            items = sorted(basket & frequent)
            for pair in combinations(items, 2):
                pair_counts[pair] += 1
            self.peak_counters = max(self.peak_counters, len(pair_counts))

        return {frozenset(p): c for p, c in pair_counts.items()
                if c >= self.support}


class YourAlgorithm:
    """Your frequent-pair finder.

        __init__(support)
        run(baskets) -> {frozenset({a, b}): count}
        .peak_counters -> the most pair counters you ever held at once

    Same pairs as the baseline. Fewer counters.

    Pass one only needs one integer per item, and there are not many items. The
    rest of your memory is sitting idle while you do it. §6.3 spends it: hash
    every pair you see in pass one into a fixed array of buckets, and count the
    buckets rather than the pairs.

    A bucket whose total is below the support threshold cannot contain a
    frequent pair. In pass two you skip every pair landing in such a bucket -
    and the bucket array collapses to a bitmap, one bit each, before you need
    the memory for counters.

    Two things to be careful of:

      * a bucket being frequent does not make its pairs frequent. It is a
        filter, not an answer
      * `peak_counters` is on your honour. Count the pair counters you hold at
        the same time. The bitmap is not a pair counter, but if you keep the
        full bucket counts alive into pass two, that is not free either -
        observation.md asks about it
    """

    def __init__(self, support, bucket_count=1 << 20):
        if support <= 0 or bucket_count <= 0:
            raise ValueError("support and bucket_count must be positive")
        self.support = support
        self.bucket_count = bucket_count
        self.peak_counters = 0
        self.bucket_bytes = 0
        self.bitmap_bytes = 0

    def _bucket(self, a, b):
        # Stable integer IDs also support the string items in Task 1.
        value = ((a + 1) * 0x9E3779B1) ^ ((b + 1) * 0x85EBCA77)
        return value % self.bucket_count

    def run(self, baskets):
        baskets = list(baskets)
        self.peak_counters = 0
        counts = Counter()
        ids = {}
        buckets = array('Q', [0]) * self.bucket_count
        self.bucket_bytes = len(buckets) * buckets.itemsize
        for basket in baskets:
            items = set(basket)
            counts.update(items)
            for item in sorted(items):
                if item not in ids:
                    ids[item] = len(ids)
            for a, b in combinations(sorted(ids[item] for item in items), 2):
                buckets[self._bucket(a, b)] += 1

        bitmap = bytearray((self.bucket_count + 7) // 8)
        for index, count in enumerate(buckets):
            if count >= self.support:
                bitmap[index >> 3] |= 1 << (index & 7)
        self.bitmap_bytes = len(bitmap)
        # Pass-two pair counters must never coexist with bucket counters.
        del buckets
        frequent = {item for item, count in counts.items() if count >= self.support}
        del counts
        pair_counts = Counter()
        for basket in baskets:
            items = sorted(set(basket) & frequent, key=ids.__getitem__)
            for a, b in combinations(items, 2):
                index = self._bucket(ids[a], ids[b])
                if bitmap[index >> 3] & (1 << (index & 7)):
                    pair_counts[(a, b)] += 1
            self.peak_counters = max(self.peak_counters, len(pair_counts))
        return {frozenset(pair): count for pair, count in pair_counts.items()
                if count >= self.support}
