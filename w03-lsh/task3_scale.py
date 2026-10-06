#!/usr/bin/env python3
"""Week 3 · Task 3 — Find the same pairs without comparing everything.

Textbook §3.4.

`BruteForce` compares every pair. On 3,000 documents that is 4.5 million
comparisons and it is completely correct. On 3 million documents it is 4.5
trillion and it is completely useless.

Beat it. Find the same near-duplicate pairs while making far fewer comparisons.

    python3 bench.py
    python3 bench.py --yours

The harness counts every call you make to `similarity()`. That is your score.
It also checks **recall** - which of the truly similar pairs you found. Skipping
comparisons is easy; skipping comparisons without losing the pairs is the task.
"""


class BruteForce:
    """Correct, and quadratic."""

    def __init__(self, threshold):
        self.threshold = threshold

    def find(self, docs, similarity):
        """docs is [set_of_shingles, ...]. Return {(i, j), ...} with i < j."""
        out = set()
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                if similarity(docs[i], docs[j]) >= self.threshold:
                    out.add((i, j))
        return out


class YourFinder:
    """Your near-duplicate finder.

        __init__(threshold)
        find(docs, similarity) -> {(i, j), ...}

    `similarity(a, b)` is the only way to compare two documents, and every call
    is counted. Everything else - signatures, banding, bucketing - is free, in
    the sense that the harness does not charge you for it. That is deliberate:
    it is also roughly true at scale, where the comparison is the expensive
    part and the hashing is linear.

    Two knobs decide everything:

        the number of hashes in a signature
        how many bands you split it into

    §3.4.2 gives you the relationship between those and the probability that a
    pair at similarity s becomes a candidate. It is an S-curve, and where its
    step sits is something you choose. Choose it on purpose and be able to say
    why in observation.md - a threshold of 0.8 does not mean bands should be
    anything in particular until you have done the arithmetic.

    You may reuse your Task 1 code.
    """

    # n=128 hashes split into b=32 bands of r=4 rows. At the threshold 0.6,
    # the S-curve 1-(1-s^r)^b sits at ~99.8% candidate probability (barely
    # any missed pairs); for the near-zero similarity of two unrelated random
    # documents it is astronomically small (almost no wasted comparisons).
    # See observation.md for the arithmetic.
    N_HASHES = 128
    BANDS = 32

    def __init__(self, threshold, n_hashes=N_HASHES, bands=BANDS, seed=20260923):
        self.threshold = threshold
        self.n_hashes = n_hashes
        self.bands = bands
        self.seed = seed

    def find(self, docs, similarity):
        import random
        from task1_minhash import minhash_signatures, lsh_candidates

        if not docs:
            return set()

        n_rows = max((e for doc in docs for e in doc), default=-1) + 1
        p = 4_294_967_311  # prime above 2**32, comfortably above any shingle id
        rng = random.Random(self.seed)
        hashes = []
        for _ in range(self.n_hashes):
            a = rng.randrange(1, p)
            b = rng.randrange(0, p)
            hashes.append(lambda r, a=a, b=b: (a * r + b) % p)

        sig = minhash_signatures(docs, hashes, n_rows)
        candidates = lsh_candidates(sig, self.bands)

        out = set()
        for i, j in candidates:
            if similarity(docs[i], docs[j]) >= self.threshold:
                out.add((i, j))
        return out
