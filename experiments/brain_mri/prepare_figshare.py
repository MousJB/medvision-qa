"""Prépare le dataset figshare : extraction, conversion .mat → PNG, manifeste, séparation
par patient, audit des doublons (voir PROTOCOL.md).

Lecture des .mat : uniquement les champs de données (label, PID, image), via h5py pour le
format MATLAB v7.3 ou scipy.io.loadmat sinon. Aucun code n'est exécuté.

    python experiments/brain_mri/prepare_figshare.py   # lit data/figshare, écrit data/figshare/png
"""

import csv
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import h5py
import numpy as np
from PIL import Image

from medvision_qa.duplicates import exact_duplicate_groups, near_duplicate_pairs, phash

ROOT = Path(__file__).resolve().parents[2]

SEED = 20261029
LABELS = {1: "meningioma", 2: "glioma", 3: "pituitary"}
SPLIT_FRACTIONS = (("train", 0.6), ("val", 0.1))  # le reste : test
NEAR_DUPLICATE_DISTANCE = 4
# Les PID « MR<nombre><lettre> » partageant une racine désignent très probablement le même
# patient (inspection visuelle, voir README.md) : on les regroupe pour la séparation.
PID_FAMILY = re.compile(r"^(MR\d+)[A-Z]$")
DATA = ROOT / "data" / "figshare"
EVAL_DIR = Path(__file__).resolve().parent / "figshare_eval"


def safe_extract(archive: Path, target: Path) -> None:
    """Extraction en refusant tout membre qui sortirait du dossier cible."""
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            destination = (target / member).resolve()
            if not destination.is_relative_to(target.resolve()):
                raise ValueError(f"membre d'archive refusé : {member!r}")
        z.extractall(target)


def read_mat(path: Path) -> tuple[int, str, np.ndarray]:
    if h5py.is_hdf5(path):
        with h5py.File(path, "r") as f:
            cj = f["cjdata"]
            label = int(np.asarray(cj["label"]).ravel()[0])
            pid = "".join(chr(int(c)) for c in np.asarray(cj["PID"]).ravel())
            image = np.asarray(cj["image"]).T  # ordre colonne de MATLAB → ligne
        return label, pid, image
    from scipy.io import loadmat
    cj = loadmat(path, squeeze_me=True, struct_as_record=False)["cjdata"]
    return int(cj.label), str(cj.PID), np.asarray(cj.image)


def to_uint8(image: np.ndarray) -> np.ndarray:
    """Min-max par image vers [0, 255], comme le code MATLAB du README figshare."""
    im = image.astype(np.float64)
    lo, hi = im.min(), im.max()
    if hi == lo:
        raise ValueError("image constante")
    return np.round(255 * (im - lo) / (hi - lo)).astype(np.uint8)


def patient_group(pid: str) -> str:
    match = PID_FAMILY.fullmatch(pid)
    return match.group(1) if match else pid


def split_patients(patient_label: dict[str, str]) -> dict[str, str]:
    rng = np.random.default_rng(SEED)
    split = {}
    for label in sorted(set(patient_label.values())):
        patients = sorted(p for p, lab in patient_label.items() if lab == label)
        patients = [patients[i] for i in rng.permutation(len(patients))]
        start = 0
        for name, fraction in SPLIT_FRACTIONS:
            n = round(fraction * len(patients))
            for p in patients[start:start + n]:
                split[p] = name
            start += n
        for p in patients[start:]:
            split[p] = "test"
    return split


def main() -> None:
    mat_dir, png_dir = DATA / "mat", DATA / "png"
    mat_dir.mkdir(exist_ok=True)
    for archive in sorted(DATA.glob("brainTumorDataPublic_*.zip")):
        safe_extract(archive, mat_dir)
    mat_files = sorted(mat_dir.rglob("*.mat"), key=lambda p: int(p.stem))
    print(f"{len(mat_files)} fichiers .mat")

    rows, hashes, pixel_digests = [], [], []
    for path in mat_files:
        label_id, pid, image = read_mat(path)
        label = LABELS[label_id]
        pixels = to_uint8(image)
        out = png_dir / label / f"{int(path.stem):04d}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels).save(out, optimize=False)
        small = np.asarray(Image.fromarray(pixels).resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
        hashes.append(phash(small))
        pixel_digests.append(hashlib.sha256(pixels.tobytes() + str(pixels.shape).encode()).hexdigest())
        rows.append({"case_id": f"fig_{int(path.stem):04d}", "source_file": path.name, "patient_id": pid,
                     "label": label, "height": pixels.shape[0], "width": pixels.shape[1],
                     "patient_group": patient_group(pid), "pixel_sha256": pixel_digests[-1],
                     "png_path": out.relative_to(DATA).as_posix()})

    # Cohérence patient → classe (patient = groupe de PID)
    labels_by_patient = defaultdict(set)
    families = defaultdict(set)
    for r in rows:
        labels_by_patient[r["patient_group"]].add(r["label"])
        families[r["patient_group"]].add(r["patient_id"])
    mixed = {p: sorted(ls) for p, ls in labels_by_patient.items() if len(ls) > 1}
    excluded = set(mixed)
    patient_label = {p: next(iter(ls)) for p, ls in labels_by_patient.items() if p not in excluded}
    split = split_patients(patient_label)
    for r in rows:
        r["split"] = split.get(r["patient_group"], "excluded")

    # Manifeste (identifiants, hashes, séparation) : versionné, sans image
    EVAL_DIR.mkdir(exist_ok=True)
    manifest = EVAL_DIR / "manifest.csv"
    fields = ["case_id", "source_file", "patient_id", "patient_group", "label", "split", "height", "width", "pixel_sha256"]
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (DATA / "png_index.json").write_text(json.dumps({r["case_id"]: r["png_path"] for r in rows}), encoding="utf-8")

    with (EVAL_DIR / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["case_id", "true_label", "patient_id"])
        for r in rows:
            if r["split"] == "test":
                writer.writerow([r["case_id"], r["label"], r["patient_group"]])

    # Audit des doublons : exacts (pixels) et quasi-doublons entre jeux
    exact = exact_duplicate_groups(pixel_digests)
    near = near_duplicate_pairs(hashes, max_distance=NEAR_DUPLICATE_DISTANCE)
    cross = [(i, j, d) for i, j, d in near if rows[i]["split"] != rows[j]["split"]]
    cross_patient = [(i, j, d) for i, j, d in near if rows[i]["patient_group"] != rows[j]["patient_group"]]
    audit = {
        "n_images": len(rows),
        "n_raw_patient_ids": len({r["patient_id"] for r in rows}),
        "n_patients": len(labels_by_patient),
        "patient_id_families_merged": {g: sorted(ids) for g, ids in sorted(families.items()) if len(ids) > 1},
        "patients_with_several_labels": mixed,
        "images_per_split": Counter(r["split"] for r in rows),
        "patients_per_split": Counter(split.values()),
        "images_per_split_and_label": Counter(f'{r["split"]}/{r["label"]}' for r in rows),
        "image_sizes": Counter(f'{r["height"]}x{r["width"]}' for r in rows),
        "exact_pixel_duplicate_groups": [[rows[i]["case_id"] for i in g] for g in exact],
        "near_duplicate_threshold": NEAR_DUPLICATE_DISTANCE,
        "near_duplicate_pairs_total": len(near),
        "near_duplicate_pairs_between_different_patients": [
            (rows[i]["case_id"], rows[j]["case_id"], d, rows[i]["split"], rows[j]["split"]) for i, j, d in cross_patient],
        "near_duplicate_pairs_across_splits": [
            (rows[i]["case_id"], rows[j]["case_id"], d, rows[i]["split"], rows[j]["split"]) for i, j, d in cross],
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }
    (EVAL_DIR / "data_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8", newline="\n")
    for key in ("n_images", "n_patients", "patients_with_several_labels", "images_per_split", "patients_per_split",
                "image_sizes", "near_duplicate_pairs_total", "manifest_sha256"):
        print(f"{key}: {audit[key]}")
    print("groupes de doublons exacts :", len(exact))
    print("quasi-doublons entre patients différents :", len(cross_patient))
    print("quasi-doublons entre jeux différents :", len(cross))


if __name__ == "__main__":
    main()
