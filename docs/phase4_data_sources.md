# Phase 4 — Data sources and plan (preparation)

[日本語](ja/phase4_data_sources.md)

Date: 2026-10-29. **Execution: see [experiments/brain_mri/README.md](../experiments/brain_mri/README.md).**
The licences and metadata below were read through the official APIs (figshare, Kaggle,
GitHub) on that date.

## 1. Candidate datasets

| Dataset | Link | Licence (declared) | Content | `patient_id` | Proposed role |
|---|---|---|---|---|---|
| **figshare — Jun Cheng** (v8, 2024-12-21) | https://figshare.com/articles/dataset/brain_tumor_dataset/1512427 · DOI `10.6084/m9.figshare.1512427.v8` | **CC BY 4.0** (checked through the figshare API) | 3,064 contrast-enhanced T1 slices, **233 patients**; meningioma 708, glioma 1,426, pituitary 930; tumour masks; `cvind.mat` (5-fold cross-validation indices); `.mat` files; ~880 MB | **yes** (`cjdata.PID`) | **Main**: train 2 versions with a patient-level split, then evaluate with a patient-level bootstrap |
| **Kaggle MRI-BT — Abou Ali** | https://www.kaggle.com/datasets/mohamadabouali1/mri-brain-tumor-dataset-4-class-7023-images · repository: https://github.com/Mohamad-AbouAli/MRIBrainTumorDataset | MIT (declared) | 7,023 images, 4 classes (including `notumor`) + 3 **synthetic** sets (Blurred, Noisy, Motion); ~139 MB | no | The dataset of the `brain-tumor-mri-classification` repository: **duplicate audit** of Training/Testing and **synthetic sensitivity tests** |
| Kaggle — Masoud Nickparvar | https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset | CC BY 4.0 (declared) | Assembled from figshare + SARTAJ + Br35H. Current version: 7,200 images (1,400 / 400 per class). An earlier version had 7,023 | no | Provenance reference; alternative |
| SARTAJ | https://www.kaggle.com/datasets/sartajbhuvaji/brain-tumor-classification-mri | MIT (declared) | Upstream source (4 classes) | no | Upstream only |
| Br35H | https://www.kaggle.com/datasets/ahmedhamada0/brain-tumor-detection | **"Data files © Original Authors"**: not an open licence | Upstream source of the `notumor` class | no | Upstream only: **do not redistribute** |

## 2. Provenance findings

- **MRI-BT (Abou Ali) ≈ first version of Nickparvar: probable, not confirmed.** Same total
  (7,023), same 4 classes, and the `brain-tumor-mri-classification` README reports 5,712
  training images. Abou Ali's Kaggle description does not cite its upstream sources. To be
  confirmed by comparing the file hashes of both datasets.
- If so, the `notumor` class comes from **Br35H**, whose licence is not open. The MIT
  licence declared on Kaggle is not enough to guarantee the rights. No image, thumbnail
  or screenshot of this dataset must therefore be published. Only aggregates and hashes
  may appear in the repository.
- figshare images appear in several of these assemblies: there is a risk of duplicates,
  or of slices of one patient, in both Training and Testing.
- A user comment on IEEE DataPort reports possible label errors among SARTAJ's gliomas.
  This is anecdotal and unverified.
- Abou Ali's "challenging" sets are **synthetic**, according to their author. They are
  sensitivity tests, not clinical conditions.

## 3. Proposed plan

1. **figshare (main).** Download the 4 zip files and `cvind.mat` (no account needed).
   Convert the `.mat` files with `h5py` if they use the MATLAB v7.3 format (to check),
   reading data fields only, without executing code. Build a SHA-256 manifest.
   Train/val/test split **by patient**. Check whether `cvind.mat` is patient-level.
2. Train **two real versions** (e.g. SimpleCNN and ResNet18, or ResNet18 with and without
   augmentation), recording seeds, configurations and weight hashes. The local GPU (GTX
   1650, 4 GB) is enough with small batches.
3. Export the predictions **with the softmax scores** and `patient_id`, in the format of
   [data_format.md](data_format.md). Evaluate with MedVision QA (unit: patient).
4. **MRI-BT (audit).** Exact duplicates (SHA-256) and near-duplicates (perceptual hash)
   between Training and Testing, then manual inspection of the flagged cases. Report the
   counts, without concluding to data leakage without proof of provenance.
5. Sensitivity tests on the synthetic sets, presented as such.

## 4. What was needed

| Item | For | State on 2026-10-29 |
|---|---|---|
| Nothing (public download) | figshare | ready |
| Kaggle account + API token (`%USERPROFILE%\.kaggle\kaggle.json`) or manual download | MRI-BT, Nickparvar | **missing** (no `.kaggle` folder) |
| PyTorch + torchvision with CUDA in a separate environment | training | to install (not added to MedVision QA's dependencies) |
| ~2 GB of disk space | data and weights | to check |
| Owner's agreement on the use (portfolio, non-commercial) given the licences | all | to confirm |

## 5. What cannot be reused from the `brain-tumor-mri-classification` repository

The notebook is empty, no weights or predictions are versioned, and the evaluation keeps
only the argmax, without scores. The README figures are therefore not reproducible;
retraining is needed. The `src/models.py` code (SimpleCNN, ResNet18) remains reusable.
