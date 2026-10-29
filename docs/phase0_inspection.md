# Phase 0 — Inspection and scoping

[日本語](ja/phase0_inspection.md)

Date: 2026-10-29

## 1. Local environment

| Item | Finding |
|---|---|
| OS | Windows 10 Home 10.0.19045 |
| Python | 3.12.6 (`C:\Python312`); project virtual environment `.venv/` |
| Installed dependencies | numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, pytest 9.2.0. Exact versions in `requirements-lock.txt` |
| git | 2.44.0; repository initialised on `main`, no commit at this stage |
| R / pROC | **absent**: no independent validation of DeLong for now (see § 4) |
| GPU | CUDA 12.3 present in the PATH; not checked and not needed before Phase 4 |

## 2. Candidate repository: `MousJB/brain-tumor-mri-classification`

Inspected through the GitHub API (read-only, no cloning, no data downloaded).

| Item | Finding |
|---|---|
| Code licence | MIT |
| Content | `src/dataset.py`, `src/models.py`, `src/utils.py`, `README.md`, `requirements.txt` |
| Notebook | `notebooks/Brain_Tumor_Classification.ipynb` is **empty** (2 bytes) |
| Checkpoints / predictions | **none** in the repository |
| Classes | glioma, meningioma, no-tumor, pituitary. The index order depends on the `classes` list passed to the `Dataset`, which is not fixed in the versioned code |

### Consequences

- The README results (94.58%, 98.09%, etc.) **cannot be reproduced from the repository**:
  the notebook that produced them is empty and no weights are versioned. They must not
  be used as reference results by MedVision QA.
- The README mentions a "validation accuracy" whereas the dataset only has `Training/`
  and `Testing/` folders. Where the validation set comes from is not documented. To be
  clarified before any reuse (Phase 4).
- `evaluate_model` keeps only the argmax: it produces **no scores**. For AUROC, the
  softmax probabilities have to be exported in the format defined in
  [data_format.md](data_format.md).
- Observation on preprocessing, to check in Phase 4 and not fixed here: after a z-score
  standardisation, the image is still divided by 255, which looks unintended.

## 3. Dataset: Kaggle "MRI Brain Tumor Dataset: 4-Class (7,023 Images)"

Metadata read through the public Kaggle API
(`mohamadabouali1/mri-brain-tumor-dataset-4-class-7023-images`, version 1).

| Item | Finding |
|---|---|
| Licence declared on Kaggle | MIT |
| Author | Mohamad Abou Ali |
| Size | ~139 MB |
| "Blurred", "Noisy", "Patient Motion Artifact" sets | described by the author as **synthetic** |

### Unverified points

- **Upstream provenance of the images**: the Kaggle description does not say where the
  7,023 images come from. If they come from earlier public datasets, the declared MIT
  licence does not guarantee the original rights. To check, for example on the GitHub
  repository cited by the author and in their papers, before any public demonstration.
- Exact duplicates and near-duplicates between `Training/` and `Testing/`: not examined
  (Phase 4).
- No patient identifier: likely, to be confirmed. Without `patient_id`, any inference
  stays at image level.

### Consequence for the report

Results on Blurred, Noisy and Motion must be presented as **sensitivity tests on
synthetic data**, not as a validation under real acquisition conditions.

## 4. DeLong

R is not installed. Per section 7 of the specification, this does not block Phase 1.
Decision (§ 6): paired bootstrap in Phase 2, DeLong marked "not implemented".

## 5. Phase 0 decisions

| Topic | Decision |
|---|---|
| Input format | [data_format.md](data_format.md): separate ground truth (recommended), one predictions CSV per version, strict alignment on `case_id` |
| Configuration and criteria | [evaluation_config.md](evaluation_config.md): TOML, criteria decided on CIs, aggregation without averaging |
| Layout | `src/medvision_qa/` (installable package) instead of `app/` (spec § 11, indicative): non-generic name, identical imports in tests and in production. Modules created phase by phase, no empty module |
| Dependencies | only what Phases 1 and 2 use (numpy, scipy, scikit-learn); FastAPI, Jinja2 and SQLite added in Phase 3/5 |
| CSV reading | planned with the standard `csv` module rather than pandas, to avoid implicit conversions (`"NA"` → NaN, type inference). To confirm in Phase 1 |

## 6. Questions settled at the end of Phase 0

| Question | Decision | Reason |
|---|---|---|
| Licence | MIT (`LICENSE`) | consistent with the MRI repository; simple for a portfolio |
| Positive class | `positive` = **list** of classes; MRI demo: tumour (`glioma`, `meningioma`, `pituitary`) vs `notumor` | the most natural clinical question for this dataset; one-vs-rest stays possible with a one-class list |
| Threshold decision rule | not supported in v0.1: `predicted_label` must be the argmax | fewer ambiguous cases; can be added later if a real need appears |
| DeLong | not implemented; AUROC compared by paired bootstrap in Phase 2 | no independent reference available (R absent); no unvalidated method exposed |

## 7. Phase 0 gate

| Condition | State |
|---|---|
| Schema and scope documented | done: `docs/data_format.md`, `docs/evaluation_config.md` |
| Reproducible environment | `.venv` + `pyproject.toml` + `requirements-lock.txt` |
| Basic tests runnable | `pytest`: 3 passed (2026-10-29) |
| Data licences and rights | declared licence identified; **upstream provenance not verified**. This does not block Phases 1 to 3, which use synthetic fixtures, but blocks Phase 4 |
