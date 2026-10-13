#!/usr/bin/env python3
"""Week 4 · Task 3 — Same memory, fewer mistakes.

Textbook §4.4 (Bloom filters), §4.5 (counting distinct).

`NaiveFilter` is a membership filter in a fixed number of bits. It works. It
also makes far more mistakes than it has to with the memory it was given, and
it does so for a reason you can find by reading §4.4.2 and doing one derivative.

You get **exactly the same number of bits**. Make fewer mistakes.

    python3 bench.py
    python3 bench.py --yours

The rule that makes this interesting: a false negative is not allowed. Ever.
The whole point of this structure is that "no" means no. A filter that gets a
better score by occasionally forgetting something it was given has not improved
anything, it has broken the contract.
"""
import hashlib, math


class NaiveFilter:
    """One hash function, and the bits it was given."""

    def __init__(self, n_bits, seed=246):
        self.n_bits = n_bits
        self.seed = seed
        self.bits = bytearray(n_bits)

    def _index(self, item):
        d = hashlib.blake2b(str(item).encode(), digest_size=8,
                            key=str(self.seed).encode()).digest()
        return int.from_bytes(d, "big") % self.n_bits

    def add(self, item):
        self.bits[self._index(item)] = 1

    def __contains__(self, item):
        return bool(self.bits[self._index(item)])

    def memory_bits(self):
        return self.n_bits


class YourFilter:
    """Your filter.

        __init__(n_bits, seed=246)
        add(item)
        item in filter  ->  bool
        memory_bits()   ->  how many bits you are using

    `memory_bits()` must not exceed the `n_bits` you were given. The harness
    checks. Counting only some of your memory is not an optimisation.

    §4.4.2 gives the false-positive rate of a filter with m bits, k hashes and
    n items inserted. There is a k that minimises it, and it depends on m/n.
    The harness tells you n before you start, so you have no excuse for guessing.

    Then there is a second question, which is worth more: the harness inserts
    a **known** number of items, but a real stream does not tell you n in
    advance. What would you do then? You do not have to implement it - but
    observation.md asks.
    """

    def __init__(self, n_bits, seed=246):
        # bench.py always inserts exactly N_INSERT items - that count is a
        # fixed constant of this exercise, not a runtime guess, so k is
        # derived from it rather than picked by trial and error. §4.4.2's
        # false-positive rate (1 - e^(-kn/m))^k is minimised at the real
        # number k* = (m/n)*ln(2); rounding it to the nearest integer is the
        # closest a real filter (whole hash functions only) can get.
        from bench import N_INSERT
        self.n_bits = n_bits
        self.seed = seed
        k_star = (n_bits / N_INSERT) * math.log(2)
        self.k = max(1, round(k_star))
        # One bit per position, packed 8 to a byte: 80,000 bits really is
        # 10,000 bytes. bytearray(n_bits) would spend a whole byte per bit.
        self.bits = bytearray((n_bits + 7) // 8)

    def _positions(self, item):
        base = str(item).encode()
        for i in range(self.k):
            d = hashlib.blake2b(base, digest_size=8,
                                 key=f"{self.seed}-{i}".encode()).digest()
            yield int.from_bytes(d, "big") % self.n_bits

    def add(self, item):
        for pos in self._positions(item):
            self.bits[pos >> 3] |= 1 << (pos & 7)

    def __contains__(self, item):
        return all(self.bits[pos >> 3] & (1 << (pos & 7))
                   for pos in self._positions(item))

    def memory_bits(self):
        # Counted from the storage actually allocated, not from the budget.
        return 8 * len(self.bits)
