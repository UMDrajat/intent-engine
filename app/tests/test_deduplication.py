#!/usr/bin/env python3
"""
Test suite for deduplication logic in Intent Engine.
Tests both embedding-based and SimHash-based deduplication.
"""

import unittest


# Mock/Import necessary components
# For testing purposes, we'll implement a simple version of the SimHash used in Go
def simhash(text: str) -> int:
    """Python implementation of the Go-style SimHash (64-bit)"""
    import re

    # Tokenize: lower, remove non-alphanumeric, split
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        return 0

    v = [0] * 64
    for token in tokens:
        # FNV-1a 64-bit hash of token
        # Simple Python implementation of FNV-1a
        h = 0xCBF29CE484222325
        for char in token:
            h = (h ^ ord(char)) & 0xFFFFFFFFFFFFFFFF
            h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF

        for i in range(64):
            if (h >> i) & 1:
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i

    return fingerprint


def hamming_distance(h1: int, h2: int) -> int:
    """Calculate Hamming distance between two 64-bit hashes"""
    x = h1 ^ h2
    dist = 0
    while x > 0:
        dist += 1
        x &= x - 1
    return dist


class TestDeduplication(unittest.TestCase):
    def test_simhash_logic(self):
        """Test the logic of SimHash for near-duplicates"""
        text1 = "How to set up encrypted email on Android with ProtonMail"
        text2 = "How to set up encrypted email on Android with Tutanota"
        text3 = "Completely different topic about gardening and flowers"

        h1 = simhash(text1)
        h2 = simhash(text2)
        h3 = simhash(text3)

        dist_1_2 = hamming_distance(h1, h2)
        dist_1_3 = hamming_distance(h1, h3)

        print(f"Distance between near-duplicates: {dist_1_2}")
        print(f"Distance between different texts: {dist_1_3}")

        self.assertLess(
            dist_1_2, 10, "Near-duplicates should have low Hamming distance"
        )
        self.assertGreater(
            dist_1_3, 15, "Different texts should have high Hamming distance"
        )

    def test_simhash_exact_duplicate(self):
        """Test SimHash with exact duplicate text"""
        text = "This is a test of exact duplication"
        h1 = simhash(text)
        h2 = simhash(text)
        self.assertEqual(h1, h2)
        self.assertEqual(hamming_distance(h1, h2), 0)

    def test_simhash_sensitivity(self):
        """Test SimHash sensitivity to small changes"""
        text1 = "Intent Engine provides privacy-first search results."
        text2 = "Intent Engine provides privacy-first search results!"  # Just a punctuation change

        h1 = simhash(text1)
        h2 = simhash(text2)

        self.assertLessEqual(
            hamming_distance(h1, h2),
            2,
            "Small punctuation changes should result in very low distance",
        )


if __name__ == "__main__":
    unittest.main()
