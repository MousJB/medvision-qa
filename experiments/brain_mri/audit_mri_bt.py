"""Duplicate audit of the Kaggle MRI-BT dataset (Abou Ali), the one used by brain-tumor-mri-classification.

- Exact duplicates: SHA-256 of the file bytes and SHA-256 of the decoded pixels.
- Near-duplicates: 64-bit pHash, Hamming distance ≤ threshold.
- Searched within Training, within Testing, between Training and Testing, and between
  MRI-BT and figshare (provenance).

Only aggregates and file names are written to the repository (``mri_bt_audit/``): no
image, since the licence of Br35H (notumor class) is not open. Contact sheets of the
flagged pairs are written to ``data/`` (not versioned) for manual inspection.

    python experiments/brain_mri/audit_mri_bt.py
"""

import csv
import hashlib
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

import kagglehub
import numpy as np
from PIL import Image

from medvision_qa.duplicates import (exact_duplicate_groups, load_grayscale, near_duplicate_pairs, phash,
                                     sha256_file)

DATASET = "mohamadabouali1/mri-brain-tumor-dataset-4-class-7023-images"
THRESHOLD = 4
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "mri_bt_audit"
SHEETS = ROOT / "data" / "mri_bt_sheets"
FIGSHARE_PNG = ROOT / "data" / "figshare" / "png"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
# Original set only: the "Challenging" sets are synthetic degradations of the same images
# and would be near-duplicates by construction.
ORIGINAL_SUBTREE = "BT-MRI Dataset"


def describe(path: Path, base: Path) -> dict:
    parts = path.relative_to(base).parts
    with Image.open(path) as im:
        pixels = np.asarray(im.convert("L"))
    return {"path": path.relative_to(base).as_posix(), "subset": parts[-3] if len(parts) >= 3 else "",
            "label": parts[-2].lower(), "file_sha256": sha256_file(path),
            "pixel_sha256": hashlib.sha256(pixels.tobytes() + str(pixels.shape).encode()).hexdigest(),
            "phash": phash(load_grayscale(path)), "size": f"{pixels.shape[0]}x{pixels.shape[1]}"}


def sheet(pairs, items, base, name, limit=24):
    """Contact sheet of side-by-side pairs (left | right) for manual inspection."""
    pairs = pairs[:limit]
    if not pairs:
        return
    tile = 160
    canvas = Image.new("L", (2 * tile + 10, len(pairs) * (tile + 10)), 255)
    for k, (i, j, _) in enumerate(pairs):
        for col, idx in enumerate((i, j)):
            with Image.open(base / items[idx]["path"]) as im:
                canvas.paste(im.convert("L").resize((tile, tile)), (col * (tile + 10), k * (tile + 10)))
    SHEETS.mkdir(parents=True, exist_ok=True)
    canvas.save(SHEETS / f"{name}.png")


def main():
    base = Path(kagglehub.dataset_download(DATASET))
    files = sorted(p for p in base.rglob("*")
                   if p.suffix.lower() in IMAGE_SUFFIXES and ORIGINAL_SUBTREE in p.relative_to(base).parts)
    print(f"{len(files)} images under {base}")
    items = [describe(p, base) for p in files]
    groups = Counter(f'{it["subset"]}/{it["label"]}' for it in items)
    print("subsets:", dict(sorted(groups.items())))

    subsets = sorted({it["subset"] for it in items})
    hashes = [it["phash"] for it in items]
    near = near_duplicate_pairs(hashes, max_distance=THRESHOLD)
    exact_file = exact_duplicate_groups([it["file_sha256"] for it in items])
    exact_pixels = exact_duplicate_groups([it["pixel_sha256"] for it in items])

    def kind(i, j):
        a, b = items[i]["subset"], items[j]["subset"]
        return f"{min(a, b)} ↔ {max(a, b)}" if a != b else f"within {a}"

    pair_kinds = Counter(kind(i, j) for i, j, _ in near)
    label_conflicts = [(i, j, d) for i, j, d in near if items[i]["label"] != items[j]["label"]]
    # Every pair within a group of byte-identical files: a group of n files gives n(n-1)/2 pairs.
    exact_pairs = [(i, j) for g in exact_file for i, j in combinations(g, 2)]
    exact_kinds = Counter(kind(i, j) for i, j in exact_pairs)
    testing_copied = sorted({i for g in exact_file for i in g if items[i]["subset"] == "Testing"
                             and any(items[j]["subset"] == "Training" for j in g)})

    OUT.mkdir(exist_ok=True)
    with (OUT / "flagged_pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["path_a", "label_a", "path_b", "label_b", "hamming", "same_pixels"])
        for i, j, d in near:
            writer.writerow([items[i]["path"], items[i]["label"], items[j]["path"], items[j]["label"], d,
                             items[i]["pixel_sha256"] == items[j]["pixel_sha256"]])

    train_test = [(i, j, d) for i, j, d in near if kind(i, j) == "Testing ↔ Training"]
    sheet([p for p in train_test if p[2] == 0], items, base, "training_testing_distance0")
    sheet([p for p in train_test if p[2] > 0], items, base, "training_testing_distance_gt0")
    sheet(label_conflicts, items, base, "label_conflicts")

    figshare = {}
    if FIGSHARE_PNG.exists():
        fig_files = sorted(FIGSHARE_PNG.rglob("*.png"))
        fig_hashes = [phash(load_grayscale(p)) for p in fig_files]
        cross = near_duplicate_pairs(hashes, fig_hashes, max_distance=THRESHOLD)
        matched = sorted({i for i, _, _ in cross})
        figshare = {
            "figshare_images": len(fig_files),
            "mri_bt_images_matching_a_figshare_image": len(matched),
            "by_subset_and_label": dict(sorted(Counter(f'{items[i]["subset"]}/{items[i]["label"]}'
                                                       for i in matched).items())),
            "label_agreement": dict(Counter(items[i]["label"] == fig_files[j].parent.name for i, j, _ in cross)),
        }

    audit = {
        "dataset": DATASET, "n_images": len(items), "subsets": subsets,
        "images_per_subset_and_label": dict(sorted(groups.items())),
        "image_sizes": dict(Counter(it["size"] for it in items).most_common(10)),
        "exact_file_duplicate_groups": len(exact_file),
        "exact_pixel_duplicate_groups": len(exact_pixels),
        "exact_file_duplicate_pairs_total": len(exact_pairs),
        "exact_file_duplicate_pairs_by_location": dict(sorted(exact_kinds.items())),
        "exact_file_duplicate_groups_with_different_labels": sum(
            len({items[i]["label"] for i in g}) > 1 for g in exact_file),
        "testing_images_with_identical_copy_in_training": {
            "count": len(testing_copied),
            "of_testing_images": sum(it["subset"] == "Testing" for it in items),
            "by_label": dict(sorted(Counter(items[i]["label"] for i in testing_copied).items())),
        },
        "near_duplicate_threshold": THRESHOLD,
        "near_duplicate_pairs_total": len(near),
        "near_duplicate_pairs_by_location": dict(pair_kinds),
        "near_duplicate_pairs_with_different_labels": len(label_conflicts),
        "provenance_vs_figshare": figshare,
    }
    (OUT / "summary.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8", newline="\n")
    print(json.dumps(audit, indent=2))  # ASCII: the Windows console may not encode "↔"


if __name__ == "__main__":
    main()
