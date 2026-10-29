"""Detection of exact duplicates and near-duplicates of images (spec § 13).

- Exact duplicate: identical SHA-256 of the file bytes, hence identical file content.
- Near-duplicate: small Hamming distance between perceptual fingerprints (64-bit DCT
  pHash). It is a **resemblance to inspect**, not proof of patient identity or of data
  leakage.

The core works on numpy arrays. Only ``load_grayscale`` depends on Pillow (``[images]``
extra).
"""

import hashlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.fft import dctn

PHASH_SIZE = 8          # 8 × 8 fingerprint = 64 bits
PHASH_INPUT = 32        # image reduced to 32 × 32 before the DCT
_BIT_WEIGHTS = (1 << np.arange(63, -1, -1, dtype=np.uint64)).astype(np.uint64)


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_grayscale(path, size: int = PHASH_INPUT) -> np.ndarray:
    """Loads an image as greyscale, resized to ``size`` × ``size`` (float64)."""
    from PIL import Image

    with Image.open(path) as image:
        return np.asarray(image.convert("L").resize((size, size), Image.Resampling.LANCZOS),
                          dtype=np.float64)


def phash(gray: np.ndarray) -> int:
    """pHash: 2D DCT of the 32 × 32 image, 8 × 8 block of low frequencies, median threshold
    (computed without the DC component)."""
    if gray.shape != (PHASH_INPUT, PHASH_INPUT):
        raise ValueError(f"{PHASH_INPUT}×{PHASH_INPUT} image expected, got {gray.shape}")
    low = dctn(gray, norm="ortho")[:PHASH_SIZE, :PHASH_SIZE]
    median = np.median(low.ravel()[1:])
    bits = (low.ravel() > median).astype(np.uint64)
    return int((bits * _BIT_WEIGHTS).sum())


def _popcount(x: np.ndarray) -> np.ndarray:
    return np.bitwise_count(x).astype(np.int64)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def near_duplicate_pairs(hashes_a, hashes_b=None, max_distance: int = 6, block: int = 2048):
    """Pairs ``(i, j, distance)`` with a distance ≤ ``max_distance``.

    Without ``hashes_b``: pairs i < j within ``hashes_a``. With it: pairs between the two
    sets. Exhaustive computation by blocks, no approximation.
    """
    a = np.asarray(hashes_a, dtype=np.uint64)
    b = a if hashes_b is None else np.asarray(hashes_b, dtype=np.uint64)
    pairs = []
    for start in range(0, len(a), block):
        distances = _popcount(a[start:start + block, None] ^ b[None, :])
        rows, cols = np.nonzero(distances <= max_distance)
        for r, c in zip(rows, cols):
            i = start + int(r)
            if hashes_b is None and int(c) <= i:
                continue
            pairs.append((i, int(c), int(distances[r, c])))
    return pairs


def exact_duplicate_groups(digests) -> list[list[int]]:
    """Groups of indices sharing the same digest (size ≥ 2), in order of appearance."""
    groups = defaultdict(list)
    for i, d in enumerate(digests):
        groups[d].append(i)
    return [g for g in groups.values() if len(g) > 1]
