# Real MRI experiment: figshare (Jun Cheng), two versions, MedVision QA evaluation

[日本語](README.ja.md)

Protocol fixed before training: [PROTOCOL.md](PROTOCOL.md) and
[figshare_eval/config.toml](figshare_eval/config.toml) (commit `6de2a12`). Sources and
licences: [docs/phase4_data_sources.md](../../docs/phase4_data_sources.md).

> Data: figshare "brain tumor dataset", Jun Cheng, v8, **CC BY 4.0**,
> DOI [10.6084/m9.figshare.1512427.v8](https://doi.org/10.6084/m9.figshare.1512427.v8).
> No image is versioned here; only identifiers, hashes and aggregates are.

## Reproduce

```bash
python -m venv .venv-train
.venv-train\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
.venv-train\Scripts\python -m pip install h5py pillow kagglehub numpy scipy
.venv-train\Scripts\python -m pip install -e . --no-deps

.venv-train\Scripts\python experiments/brain_mri/download_figshare.py     # MD5 checked
.venv-train\Scripts\python experiments/brain_mri/prepare_figshare.py      # PNG, manifest, split, audit
.venv-train\Scripts\python experiments/brain_mri/train.py simplecnn
.venv-train\Scripts\python experiments/brain_mri/train.py resnet18
python -m medvision_qa experiments/brain_mri/figshare_eval/config.toml -o experiments/brain_mri/figshare_eval/report.html
python -m medvision_qa experiments/brain_mri/figshare_eval/config.ja.toml -o experiments/brain_mri/figshare_eval/report.ja.html --lang ja
```

## 1. Data preparation and audit

| Item | Result |
|---|---|
| Files | 3,064 `.mat` files (MATLAB v7.3 / HDF5), read with h5py: fields `label`, `PID`, `image` only |
| Sizes | 3,049 at 512×512, 15 at 256×256 |
| Raw PIDs | 233; no PID linked to two classes |
| Exact duplicates (pixels) | **0** |
| Near-duplicates (pHash, distance ≤ 4) | 724 pairs, mostly neighbouring slices of the same patient |

### Finding: one patient under several PIDs

PIDs of the form `MR<number><letter>` (43 PIDs, all gliomas) form **18 families sharing
a root** (e.g. `MR024780B`, `D`, `E`, `G`). With a split on raw PIDs, **12 families were
spread across training, validation and test.**

Visual inspection (contact sheets in `data/inspection/`, not versioned): the slices of
`MR024780D` (test) and `MR024780E` (training) are near-identical (same head, same
lesion). `MR049453` / `MR049453B`, `MR051644B` / `MR051644C` and `MR040240` /
`MR040240D` show the same anatomy and the same lesion, with differences consistent with
scans on different dates. This is not a radiological opinion.

**Decision (protocol deviation, taken before any training)**: one patient = the PID root.
This gives 209 patients, and the split gives **125 / 20 / 64 patients**
(1,996 / 292 / 776 images). It is the cautious choice: wrongly merging two patients only
shrinks the sample, while keeping them apart risked a leak into the test set. The
acceptance criteria did not change.

### Near-duplicates between different patients: false positives

After grouping, 69 pairs link different patients, 38 of them across different sets. **All
38 pairs were inspected**: the lesions, heads and contrasts differ; only the slice
orientation (mid-sagittal, axial) looks alike, and 11 of these pairs even match a
meningioma with a glioma. A pHash with a threshold of 4 is too permissive for brain MRI:
it flags resemblance, it proves nothing.

Details: [figshare_eval/data_audit.json](figshare_eval/data_audit.json),
[figshare_eval/manifest.csv](figshare_eval/manifest.csv).

## 2. Audit of the Kaggle MRI-BT dataset (the one used by `brain-tumor-mri-classification`)

Script: [audit_mri_bt.py](audit_mri_bt.py). Results:
[mri_bt_audit/summary.json](mri_bt_audit/summary.json) and
[mri_bt_audit/flagged_pairs.csv](mri_bt_audit/flagged_pairs.csv) (file names only: no
image is versioned, since the Br35H licence is not open). Scope: the original BT-MRI set
(Training 5,712, Testing 1,311, every image at 224×224). The "Challenging" sets are
excluded, since by construction they are degradations of the same images.

| Finding | Value |
|---|---|
| Groups of **byte-identical** files | 300 (695 pairs) |
| **Training ↔ Testing** identical pairs | 365 |
| **Testing images with an identical copy in Training** | **216 / 1,311 (16.5%)**: meningioma 106, no-tumor 105, pituitary 5 (recounted independently on 2026-10-29) |
| Identical duplicates with different labels | 0 |
| Near-duplicates (pHash ≤ 4) with different labels | 50; **24 inspected**: all show different images, hence false positives (the other 26 were not inspected) |
| MRI-BT images close to a figshare image (pHash ≤ 4) | 1,704 (mostly Training meningioma and pituitary), labels agree in 98% of the pairs |

**What can be stated.** 16.5% of the MRI-BT test images are exact copies of training
images. An evaluation on this Training/Testing split is therefore not independent for
these images, and the performance published on this split (including the figures in the
`brain-tumor-mri-classification` README, which now says so) is probably optimistic. The
size of this bias was not measured.

**What cannot be stated.** An identical file proves an identical image, not the identity
of a patient. Since MRI-BT has no `patient_id`, it is impossible to check whether other
slices of the same patient are spread across both sets. The match with figshare (1,704
images) is consistent with an assembly that includes figshare, without proving it on its
own.

## 3. Training the two versions

| | A — SimpleCNN | B — ResNet18 (ImageNet) |
|---|---|---|
| Best epoch (validation macro-F1) | 13 (0.850) | 15 (0.954) |
| Duration (GTX 1650) | 169 s | 196 s |
| SHA-256 of the weights | `7b17a4a3…5127d2` | `a8901dd2…25d73f5` |
| Full log | [training_simplecnn.json](figshare_eval/training_simplecnn.json) | [training_resnet18.json](figshare_eval/training_resnet18.json) |

Environment: torch 2.14.1+cu126, torchvision, Python 3.12.6. The weights are not
versioned; they are in `data/models/` and identified by their SHA-256.

**Code.** The training logs state `code_commit = dedb768`, which was HEAD at run time,
while `train.py` was not yet committed. The code that ran was committed unchanged in
`2bcfb77`: identical content, checked by SHA-256 after normalising line endings. That
commit is the one declared in `config.toml`.

**Partial determinism.** Seeds are fixed and deterministic algorithms are requested
(`warn_only`), but some CUDA operations have no deterministic version. A new training run
may therefore give slightly different weights.

## 4. MedVision QA evaluation (test: 776 slices, 64 patients)

Reports: [figshare_eval/report.html](figshare_eval/report.html) (English) and
[figshare_eval/report.ja.html](figshare_eval/report.ja.html) (Japanese). 95% intervals,
percentile bootstrap **by patient** (64 units), 2,000 draws.

| Criterion (fixed before training) | Result | State |
|---|---|---|
| C1 — macro-F1 of B not inferior to A (margin 0.03) | Δ = +0.129, CI [0.074; 0.188] | **SATISFIED** |
| C2 — glioma sensitivity of B ≥ 0.90 | 0.929, CI [0.865; 0.970] | **INCONCLUSIVE** |
| C3 — glioma AUROC of B higher than A | 0.916 → 0.990, Δ CI [0.031; 0.135] | **SATISFIED** |
| **Overall decision** | | **INCONCLUSIVE** |

| Metric | A — SimpleCNN | B — ResNet18 |
|---|---|---|
| Accuracy | 0.800 [0.730; 0.860] | 0.928 [0.875; 0.968] |
| Macro-F1 | 0.795 [0.717; 0.851] | 0.923 [0.867; 0.964] |
| Recall glioma / meningioma / pituitary | 0.800 / 0.750 / 0.835 | 0.929 / 0.934 / 0.923 |
| Specificity (glioma vs others) | 0.844 | 0.969 |
| AUROC (glioma vs others) | 0.916 | 0.990 |

**Reading.** B is clearly better than A on these data. But **C2 is not demonstrated**: the
glioma sensitivity estimate (0.929) is above 0.90, while the interval, with 64 patients,
still contains 0.90. Concluding "pass" from the point estimate would be an
over-interpretation, and that is what the INCONCLUSIVE state prevents. Settling it would
need more test patients, or a criterion and a sample-size justification defined
accordingly.

McNemar does **not apply** (several slices per patient). DeLong is not implemented; the
AUROC difference comes from the paired bootstrap.

## 5. Limits

- One dataset (2 hospitals in China, scans from 2005 to 2010, contrast-enhanced T1): no
  external validation, and the results do not transfer to other acquisitions.
- Grouping PIDs rests on an assumption (same root = same patient) supported by a
  non-expert visual inspection.
- Validation set of 20 patients: epoch selection is noisy (A's validation macro-F1 varies
  from 0.54 to 0.85 between epochs).
- Per-image min-max and resizing to 224×224 lose information. No hyperparameter tuning was
  done: this is not an optimised comparison of the two architectures.
- No robustness tests on these models. The MRI-BT "Challenging" sets have 4 classes
  (including notumor) and do not match the 3-class figshare task.
- None of these analyses is a clinical validation.

## 6. Note on the English translation

The repository was translated from French into English (and Japanese versions added) after
the evaluation. Only free text changed: comments, messages, descriptions in
`config.toml`, the descriptive fields `augmentation`, `selection` and `determinism` of
`training_*.json`, and the "within" keys of `mri_bt_audit/summary.json`. Every number,
hash, criterion and threshold is unchanged; the original French files remain in the git
history (commit `3a387f5` and earlier). The reports were regenerated from the translated
configuration, which is why their configuration hash differs from the one of commit
`6de2a12`.
