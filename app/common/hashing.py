"""Hashing utilities for content fingerprinting and deduplication."""

import hashlib
import re
from typing import Sequence


def normalize_text(text: str) -> str:
    """Normalize text for consistent hashing.

    - Lowercase
    - Remove extra whitespace
    - Remove punctuation
    - Strip leading/trailing whitespace

    Args:
        text: Input text.

    Returns:
        Normalized text.
    """
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Remove punctuation (keep alphanumeric and spaces)
    text = re.sub(r"[^\w\s]", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def compute_text_hash(text: str, *, normalize: bool = True) -> str:
    """Compute SHA256 hash of text.

    Args:
        text: Input text.
        normalize: Whether to normalize text before hashing.

    Returns:
        Hex-encoded hash string.
    """
    if normalize:
        text = normalize_text(text)

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_content_fingerprint(
    title: str,
    content: str | None = None,
    *,
    url: str | None = None,
) -> str:
    """Compute a content fingerprint for deduplication.

    Combines title and content (if available) into a single fingerprint.

    Args:
        title: Content title.
        content: Optional content body.
        url: Optional URL (used as fallback).

    Returns:
        Hex-encoded fingerprint.
    """
    parts = [normalize_text(title)]

    if content:
        # Use first 500 chars of normalized content
        normalized_content = normalize_text(content)[:500]
        parts.append(normalized_content)
    elif url:
        # Fallback to URL if no content
        parts.append(url.lower())

    combined = "|".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def compute_simhash(text: str, *, hash_bits: int = 64) -> int:
    """Compute SimHash for near-duplicate detection.

    SimHash is a locality-sensitive hash that produces similar
    hashes for similar content.

    Args:
        text: Input text.
        hash_bits: Number of bits in the hash.

    Returns:
        SimHash as integer.
    """
    if not text:
        return 0

    # Tokenize
    tokens = normalize_text(text).split()
    if not tokens:
        return 0

    # Initialize bit counts
    bit_counts = [0] * hash_bits

    for token in tokens:
        # Hash each token
        token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)

        # Update bit counts
        for i in range(hash_bits):
            if token_hash & (1 << i):
                bit_counts[i] += 1
            else:
                bit_counts[i] -= 1

    # Generate final hash
    simhash = 0
    for i in range(hash_bits):
        if bit_counts[i] > 0:
            simhash |= 1 << i

    return simhash


def hamming_distance(hash1: int, hash2: int, *, bits: int = 64) -> int:
    """Compute Hamming distance between two hashes.

    Args:
        hash1: First hash.
        hash2: Second hash.
        bits: Number of bits to compare.

    Returns:
        Number of differing bits.
    """
    xor = hash1 ^ hash2
    distance = 0
    for _ in range(bits):
        distance += xor & 1
        xor >>= 1
    return distance


def simhash_similarity(hash1: int, hash2: int, *, bits: int = 64) -> float:
    """Compute similarity between two SimHashes.

    Args:
        hash1: First SimHash.
        hash2: Second SimHash.
        bits: Number of bits in the hashes.

    Returns:
        Similarity score in range [0, 1].
    """
    distance = hamming_distance(hash1, hash2, bits=bits)
    return 1.0 - (distance / bits)


def compute_shingle_hashes(
    text: str,
    *,
    shingle_size: int = 3,
    num_hashes: int = 100,
) -> set[int]:
    """Compute MinHash shingles for text.

    Args:
        text: Input text.
        shingle_size: Number of words per shingle.
        num_hashes: Number of hash functions to use.

    Returns:
        Set of minimum hash values.
    """
    tokens = normalize_text(text).split()
    if len(tokens) < shingle_size:
        return set()

    # Generate shingles
    shingles: set[str] = set()
    for i in range(len(tokens) - shingle_size + 1):
        shingle = " ".join(tokens[i : i + shingle_size])
        shingles.add(shingle)

    if not shingles:
        return set()

    # Compute MinHash signature
    min_hashes: set[int] = set()
    for i in range(num_hashes):
        min_hash = float("inf")
        for shingle in shingles:
            # Use different hash for each iteration
            h = int(
                hashlib.md5(f"{i}:{shingle}".encode("utf-8")).hexdigest()[:8], 16
            )
            min_hash = min(min_hash, h)
        min_hashes.add(int(min_hash))

    return min_hashes


def jaccard_from_minhash(
    hashes1: set[int],
    hashes2: set[int],
) -> float:
    """Estimate Jaccard similarity from MinHash signatures.

    Args:
        hashes1: First MinHash signature.
        hashes2: Second MinHash signature.

    Returns:
        Estimated Jaccard similarity in range [0, 1].
    """
    if not hashes1 or not hashes2:
        return 0.0

    intersection = len(hashes1 & hashes2)
    union = len(hashes1 | hashes2)

    return intersection / union if union > 0 else 0.0


def stable_feature_hash(features: Sequence[str]) -> str:
    """Compute stable hash from a sequence of features.

    Features are sorted before hashing to ensure stability.

    Args:
        features: List of feature strings.

    Returns:
        Hex-encoded hash.
    """
    # Sort and join features
    sorted_features = sorted(set(features))
    combined = "|".join(sorted_features)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def url_fingerprint(url: str) -> str:
    """Compute fingerprint for URL normalization.

    Normalizes URL before hashing:
    - Lowercase
    - Remove trailing slashes
    - Remove common tracking parameters

    Args:
        url: Input URL.

    Returns:
        Hex-encoded fingerprint.
    """
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    if not url:
        return ""

    # Parse URL
    parsed = urlparse(url.lower())

    # Remove tracking parameters
    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "source",
        "fbclid",
        "gclid",
    }

    query_params = parse_qs(parsed.query)
    filtered_params = {
        k: v for k, v in query_params.items() if k.lower() not in tracking_params
    }

    # Rebuild URL
    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            parsed.params,
            urlencode(filtered_params, doseq=True) if filtered_params else "",
            "",  # Remove fragment
        )
    )

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
