"""Détection de doublons exacts et de quasi-doublons d'images (spec § 13).

- Doublon exact : SHA-256 identique des octets du fichier, donc même contenu de fichier.
- Quasi-doublon : distance de Hamming faible entre empreintes perceptuelles (pHash DCT
  64 bits). C'est une **ressemblance à examiner**, pas une preuve d'identité de patient
  ni de fuite de données.

Le cœur travaille sur des tableaux numpy. Seul ``load_grayscale`` dépend de Pillow
(extra ``[images]``).
"""

import hashlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.fft import dctn

PHASH_SIZE = 8          # empreinte 8 × 8 = 64 bits
PHASH_INPUT = 32        # image réduite à 32 × 32 avant la DCT
_BIT_WEIGHTS = (1 << np.arange(63, -1, -1, dtype=np.uint64)).astype(np.uint64)


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_grayscale(path, size: int = PHASH_INPUT) -> np.ndarray:
    """Charge une image en niveaux de gris redimensionnée à ``size`` × ``size`` (float64)."""
    from PIL import Image

    with Image.open(path) as image:
        return np.asarray(image.convert("L").resize((size, size), Image.Resampling.LANCZOS),
                          dtype=np.float64)


def phash(gray: np.ndarray) -> int:
    """pHash : DCT 2D de l'image 32 × 32, bloc 8 × 8 des basses fréquences, seuil médian
    (calculé hors composante continue)."""
    if gray.shape != (PHASH_INPUT, PHASH_INPUT):
        raise ValueError(f"image {PHASH_INPUT}×{PHASH_INPUT} attendue, reçu {gray.shape}")
    low = dctn(gray, norm="ortho")[:PHASH_SIZE, :PHASH_SIZE]
    median = np.median(low.ravel()[1:])
    bits = (low.ravel() > median).astype(np.uint64)
    return int((bits * _BIT_WEIGHTS).sum())


def _popcount(x: np.ndarray) -> np.ndarray:
    return np.bitwise_count(x).astype(np.int64)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def near_duplicate_pairs(hashes_a, hashes_b=None, max_distance: int = 6, block: int = 2048):
    """Paires ``(i, j, distance)`` avec une distance ≤ ``max_distance``.

    Sans ``hashes_b`` : paires i < j au sein de ``hashes_a``. Avec : paires entre les deux
    ensembles. Calcul exhaustif par blocs, sans approximation.
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
    """Groupes d'indices partageant le même condensat (taille ≥ 2), dans l'ordre d'apparition."""
    groups = defaultdict(list)
    for i, d in enumerate(digests):
        groups[d].append(i)
    return [g for g in groups.values() if len(g) > 1]
