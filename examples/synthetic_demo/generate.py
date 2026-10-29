"""Generates the SYNTHETIC CSV files of the demo (no real data).

Simulates two versions of a 4-class MRI classifier on 450 patients (1 to 3 images each).
Difficulty is shared by the images of one patient, which makes the cases correlated and
justifies the patient-level bootstrap. Version B is built slightly better than A.

    python examples/synthetic_demo/generate.py
"""

from pathlib import Path

import numpy as np

CLASSES = ("glioma", "meningioma", "notumor", "pituitary")
SEED = 20261029
HERE = Path(__file__).resolve().parent


def simulate_scores(rng, y, difficulty, strength):
    n, k = len(y), len(CLASSES)
    logits = rng.normal(0, 1, (n, k))
    logits[np.arange(n), y] += strength - difficulty
    p = np.exp(logits)
    return p / p.sum(axis=1, keepdims=True)


def write_predictions(path, case_ids, scores):
    rounded = np.round(scores, 6)
    lines = ["case_id,predicted_label," + ",".join(f"score_{c}" for c in CLASSES)]
    for case_id, row in zip(case_ids, rounded):
        lines.append(f"{case_id},{CLASSES[int(np.argmax(row))]}," + ",".join(f"{v:.6f}" for v in row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(out_dir: Path = HERE):
    rng = np.random.default_rng(SEED)
    n_patients = 450
    images_per_patient = rng.integers(1, 4, n_patients)
    patient_class = rng.choice(len(CLASSES), n_patients, p=[0.25, 0.25, 0.28, 0.22])
    patient_difficulty = rng.gamma(2.0, 0.6, n_patients)

    patients = np.repeat(np.arange(n_patients), images_per_patient)
    y = patient_class[patients]
    difficulty = patient_difficulty[patients]
    case_ids = [f"img_{i:05d}" for i in range(len(y))]

    gt = ["case_id,true_label,patient_id"]
    gt += [f"{c},{CLASSES[t]},P{p:04d}" for c, t, p in zip(case_ids, y, patients)]
    (out_dir / "ground_truth.csv").write_text("\n".join(gt) + "\n", encoding="utf-8", newline="\n")
    write_predictions(out_dir / "preds_v1.csv", case_ids, simulate_scores(rng, y, difficulty, 3.2))
    write_predictions(out_dir / "preds_v2.csv", case_ids, simulate_scores(rng, y, difficulty, 3.6))
    print(f"{len(y)} images, {n_patients} patients written to {out_dir}")


if __name__ == "__main__":
    main()
