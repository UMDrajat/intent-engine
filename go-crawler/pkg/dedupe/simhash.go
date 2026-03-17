package dedupe

import (
	"hash/fnv"
	"strings"
	"unicode"
)

// SimHash 64-bit fingerprint
type SimHash uint64

// NewSimHash generates a 64-bit SimHash for the given text
func NewSimHash(text string) SimHash {
	v := make([]int, 64)
	
	// Tokenize and clean text
	words := tokenize(text)
	if len(words) == 0 {
		return 0
	}

	for _, word := range words {
		// Use FNV-1a for fast hashing of tokens
		h := fnv.New64a()
		h.Write([]byte(word))
		hash := h.Sum64()
		
		for i := 0; i < 64; i++ {
			if (hash >> uint(i) & 1) == 1 {
				v[i]++
			} else {
				v[i]--
			}
		}
	}
	
	var fingerprint uint64
	for i := 0; i < 64; i++ {
		if v[i] > 0 {
			fingerprint |= 1 << uint(i)
		}
	}
	return SimHash(fingerprint)
}

// HammingDistance calculates the number of bits that differ
func (s SimHash) HammingDistance(other SimHash) int {
	x := uint64(s ^ other)
	dist := 0
	for x > 0 {
		dist++
		x &= x - 1
	}
	return dist
}

// IsNearDuplicate returns true if the distance is below the threshold (typically 3)
func (s SimHash) IsNearDuplicate(other SimHash, threshold int) bool {
	return s.HammingDistance(other) <= threshold
}

// tokenize breaks text into words, removes punctuation and converts to lowercase
func tokenize(text string) []string {
	return strings.FieldsFunc(strings.ToLower(text), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsNumber(r)
	})
}
