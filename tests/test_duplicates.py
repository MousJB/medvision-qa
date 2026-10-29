import itertools

import numpy as np
import pytest

from medvision_qa.duplicates import (exact_duplicate_groups, hamming, load_grayscale,
                                     near_duplicate_pairs, phash, sha256_file)


def blobs(seed, n=32):
    """Smooth synthetic image (sum of Gaussians), close to an anatomical structure."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n]
    img = np.zeros((n, n))
    for _ in range(5):
        cx, cy, s = rng.uniform(4, n - 4), rng.uniform(4, n - 4), rng.uniform(2, 8)
        img += rng.uniform(50, 200) * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s ** 2))
    return img


def test_phash_identical_for_identical_images():
    assert phash(blobs(1)) == phash(blobs(1).copy())


def test_phash_robust_to_small_noise_and_brightness():
    img = blobs(2)
    noisy = img + np.random.default_rng(0).normal(0, 2, img.shape)
    brighter = img * 1.1 + 10
    assert hamming(phash(img), phash(noisy)) <= 6
    assert hamming(phash(img), phash(brighter)) <= 2


def test_phash_separates_different_images():
    distances = [hamming(phash(blobs(a)), phash(blobs(b))) for a, b in itertools.combinations(range(10), 2)]
    assert min(distances) > 6


def test_phash_rejects_wrong_size():
    with pytest.raises(ValueError):
        phash(np.zeros((16, 16)))


def test_near_duplicate_pairs_matches_brute_force():
    rng = np.random.default_rng(0)
    base = rng.integers(0, 2 ** 63, 50, dtype=np.uint64)
    flips = rng.integers(0, 64, (50, 3))
    variants = [int(h) ^ sum(1 << int(f) for f in fs[: rng.integers(0, 4)]) for h, fs in zip(base, flips)]
    hashes = [int(h) for h in base] + variants
    expected = sorted((i, j, hamming(hashes[i], hashes[j]))
                      for i, j in itertools.combinations(range(len(hashes)), 2)
                      if hamming(hashes[i], hashes[j]) <= 4)
    assert sorted(near_duplicate_pairs(hashes, max_distance=4, block=7)) == expected
    assert len(expected) >= 50  # every variant finds its original


def test_near_duplicate_pairs_between_sets():
    a, b = [0b1111, 1 << 40], [0b1110, 0b0, (1 << 40) | 1]
    # 1 << 40 and 0 differ by one bit only: distance 1 as well
    assert sorted(near_duplicate_pairs(a, b, max_distance=1)) == [(0, 0, 1), (1, 1, 1), (1, 2, 1)]
    assert near_duplicate_pairs(a, b, max_distance=0) == []


def test_exact_duplicate_groups():
    assert exact_duplicate_groups(["x", "y", "x", "z", "y", "x"]) == [[0, 2, 5], [1, 4]]
    assert exact_duplicate_groups(["a", "b"]) == []


def test_file_level_helpers(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    img = blobs(3, n=128)
    a, b, c = tmp_path / "a.png", tmp_path / "b.png", tmp_path / "c.png"
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(a)
    b.write_bytes(a.read_bytes())
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).resize((256, 256)).save(c)
    assert sha256_file(a) == sha256_file(b) != sha256_file(c)
    # same content at another resolution: near-duplicate, not exact duplicate
    assert hamming(phash(load_grayscale(a)), phash(load_grayscale(c))) <= 4
