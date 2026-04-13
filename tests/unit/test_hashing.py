"""Unit tests for hashing utilities."""

import pytest

from app.common.hashing import (
    compute_content_fingerprint,
    compute_shingle_hashes,
    compute_simhash,
    compute_text_hash,
    hamming_distance,
    jaccard_from_minhash,
    normalize_text,
    simhash_similarity,
    stable_feature_hash,
    url_fingerprint,
)


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_lowercase(self) -> None:
        """Should convert to lowercase."""
        assert normalize_text("Hello World") == "hello world"

    def test_remove_punctuation(self) -> None:
        """Should remove punctuation."""
        assert normalize_text("Hello, World!") == "hello world"

    def test_normalize_whitespace(self) -> None:
        """Should normalize whitespace."""
        assert normalize_text("hello   world") == "hello world"
        assert normalize_text("  hello  world  ") == "hello world"

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert normalize_text("") == ""

    def test_only_punctuation(self) -> None:
        """Should handle string with only punctuation."""
        assert normalize_text("!!!") == ""


class TestComputeTextHash:
    """Tests for compute_text_hash function."""

    def test_deterministic(self) -> None:
        """Same text should produce same hash."""
        hash1 = compute_text_hash("hello world")
        hash2 = compute_text_hash("hello world")
        assert hash1 == hash2

    def test_different_texts_differ(self) -> None:
        """Different texts should produce different hashes."""
        hash1 = compute_text_hash("hello world")
        hash2 = compute_text_hash("goodbye world")
        assert hash1 != hash2

    def test_normalization(self) -> None:
        """Should normalize before hashing by default."""
        hash1 = compute_text_hash("Hello World!")
        hash2 = compute_text_hash("hello world")
        assert hash1 == hash2

    def test_without_normalization(self) -> None:
        """Should not normalize when disabled."""
        hash1 = compute_text_hash("Hello World!", normalize=False)
        hash2 = compute_text_hash("hello world", normalize=False)
        assert hash1 != hash2

    def test_returns_hex_string(self) -> None:
        """Should return hex-encoded string."""
        result = compute_text_hash("test")
        assert all(c in "0123456789abcdef" for c in result)
        assert len(result) == 64  # SHA256 produces 64 hex chars


class TestComputeContentFingerprint:
    """Tests for compute_content_fingerprint function."""

    def test_title_only(self) -> None:
        """Should work with title only."""
        fp = compute_content_fingerprint("Test Title")
        assert len(fp) == 64

    def test_title_and_content(self) -> None:
        """Should combine title and content."""
        fp1 = compute_content_fingerprint("Title", "Content A")
        fp2 = compute_content_fingerprint("Title", "Content B")
        assert fp1 != fp2

    def test_url_fallback(self) -> None:
        """Should use URL as fallback when no content."""
        fp1 = compute_content_fingerprint("Title", url="https://example.com/a")
        fp2 = compute_content_fingerprint("Title", url="https://example.com/b")
        assert fp1 != fp2


class TestComputeSimhash:
    """Tests for compute_simhash function."""

    def test_returns_integer(self) -> None:
        """Should return integer hash."""
        result = compute_simhash("hello world test")
        assert isinstance(result, int)

    def test_empty_text(self) -> None:
        """Should return 0 for empty text."""
        assert compute_simhash("") == 0

    def test_similar_texts_similar_hash(self) -> None:
        """Similar texts should have similar hashes."""
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "The quick brown fox leaps over the lazy dog"

        hash1 = compute_simhash(text1)
        hash2 = compute_simhash(text2)

        # Should have high similarity (low hamming distance)
        similarity = simhash_similarity(hash1, hash2)
        assert similarity > 0.7

    def test_different_texts_different_hash(self) -> None:
        """Very different texts should have different hashes."""
        text1 = "Machine learning and artificial intelligence"
        text2 = "Cooking recipes and kitchen tips"

        hash1 = compute_simhash(text1)
        hash2 = compute_simhash(text2)

        similarity = simhash_similarity(hash1, hash2)
        assert similarity < 0.8


class TestHammingDistance:
    """Tests for hamming_distance function."""

    def test_identical_hashes(self) -> None:
        """Identical hashes should have distance 0."""
        assert hamming_distance(0b1010, 0b1010) == 0

    def test_one_bit_difference(self) -> None:
        """Should count single bit difference."""
        assert hamming_distance(0b1010, 0b1011) == 1

    def test_all_bits_different(self) -> None:
        """Should count all different bits."""
        assert hamming_distance(0b0000, 0b1111, bits=4) == 4


class TestSimhashSimilarity:
    """Tests for simhash_similarity function."""

    def test_identical_hashes(self) -> None:
        """Identical hashes should have similarity 1.0."""
        assert simhash_similarity(123, 123) == 1.0

    def test_completely_different(self) -> None:
        """Completely different hashes should have similarity 0.0."""
        # All bits different in 4-bit comparison
        assert simhash_similarity(0b0000, 0b1111, bits=4) == 0.0


class TestComputeShingleHashes:
    """Tests for compute_shingle_hashes function."""

    def test_returns_set(self) -> None:
        """Should return set of hashes."""
        result = compute_shingle_hashes("one two three four five")
        assert isinstance(result, set)
        assert len(result) > 0

    def test_short_text(self) -> None:
        """Should return empty set for text shorter than shingle size."""
        result = compute_shingle_hashes("one two", shingle_size=3)
        assert result == set()

    def test_similar_texts_overlap(self) -> None:
        """Similar texts should have overlapping shingles."""
        text1 = "the quick brown fox jumps"
        text2 = "the quick brown dog jumps"

        hashes1 = compute_shingle_hashes(text1)
        hashes2 = compute_shingle_hashes(text2)

        # Should have some overlap
        overlap = len(hashes1 & hashes2)
        assert overlap > 0


class TestJaccardFromMinhash:
    """Tests for jaccard_from_minhash function."""

    def test_identical_sets(self) -> None:
        """Identical sets should have similarity 1.0."""
        hashes = {1, 2, 3, 4, 5}
        assert jaccard_from_minhash(hashes, hashes) == 1.0

    def test_disjoint_sets(self) -> None:
        """Disjoint sets should have low similarity."""
        hashes1 = {1, 2, 3}
        hashes2 = {4, 5, 6}
        assert jaccard_from_minhash(hashes1, hashes2) == 0.0

    def test_partial_overlap(self) -> None:
        """Partial overlap should have moderate similarity."""
        hashes1 = {1, 2, 3, 4}
        hashes2 = {3, 4, 5, 6}
        # Intersection: {3, 4}, Union: {1, 2, 3, 4, 5, 6}
        assert jaccard_from_minhash(hashes1, hashes2) == pytest.approx(2 / 6)

    def test_empty_sets(self) -> None:
        """Empty sets should return 0.0."""
        assert jaccard_from_minhash(set(), {1, 2}) == 0.0
        assert jaccard_from_minhash({1, 2}, set()) == 0.0


class TestStableFeatureHash:
    """Tests for stable_feature_hash function."""

    def test_deterministic(self) -> None:
        """Same features should produce same hash."""
        features = ["a", "b", "c"]
        hash1 = stable_feature_hash(features)
        hash2 = stable_feature_hash(features)
        assert hash1 == hash2

    def test_order_independent(self) -> None:
        """Order should not affect hash."""
        hash1 = stable_feature_hash(["a", "b", "c"])
        hash2 = stable_feature_hash(["c", "a", "b"])
        assert hash1 == hash2

    def test_duplicates_ignored(self) -> None:
        """Duplicates should be ignored."""
        hash1 = stable_feature_hash(["a", "b", "c"])
        hash2 = stable_feature_hash(["a", "a", "b", "c"])
        assert hash1 == hash2


class TestUrlFingerprint:
    """Tests for url_fingerprint function."""

    def test_basic_url(self) -> None:
        """Should fingerprint basic URL."""
        fp = url_fingerprint("https://example.com/page")
        assert len(fp) == 16

    def test_removes_tracking_params(self) -> None:
        """Should remove tracking parameters."""
        fp1 = url_fingerprint("https://example.com/page")
        fp2 = url_fingerprint("https://example.com/page?utm_source=twitter")
        assert fp1 == fp2

    def test_removes_trailing_slash(self) -> None:
        """Should normalize trailing slashes."""
        fp1 = url_fingerprint("https://example.com/page")
        fp2 = url_fingerprint("https://example.com/page/")
        assert fp1 == fp2

    def test_case_insensitive(self) -> None:
        """Should be case insensitive."""
        fp1 = url_fingerprint("https://Example.COM/Page")
        fp2 = url_fingerprint("https://example.com/page")
        assert fp1 == fp2

    def test_empty_url(self) -> None:
        """Should handle empty URL."""
        assert url_fingerprint("") == ""

    def test_preserves_meaningful_params(self) -> None:
        """Should preserve non-tracking parameters."""
        fp1 = url_fingerprint("https://example.com/search?q=test")
        fp2 = url_fingerprint("https://example.com/search?q=other")
        assert fp1 != fp2
