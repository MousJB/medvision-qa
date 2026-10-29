# Protocol of the figshare MRI experiment — fixed before training

[日本語](PROTOCOL.ja.md)

Date: 2026-10-29. This document and `figshare_eval/config.toml` were committed **before**
the first training run (commit `6de2a12`, original French version). Any later deviation is
reported in `README.md`. This English translation changes no rule.

## Data

- figshare "brain tumor dataset", Jun Cheng, v8, CC BY 4.0. Download checked by MD5
  (`download_figshare.py`).
- 3,064 slices, 233 patients, 3 classes: glioma, meningioma, pituitary. `case_id` = number
  of the `.mat` file; `patient_id` = `cjdata.PID`.

## Split

- **By patient**, stratified by class: each patient has only one tumour type. If a patient
  appears with several classes, the anomaly is reported and the patient is excluded, with
  documentation.
- 60% of the patients for training, 10% for validation, 30% for testing. Seed 20261029.
- The test set is used only once, to produce the final predictions. No tuning is done on
  the test set.

## Models (two versions)

| Version | Model | Training |
|---|---|---|
| A | SimpleCNN (architecture of `MousJB/brain-tumor-mri-classification`) | from scratch |
| B | torchvision ResNet18 pretrained on ImageNet | all layers |

Shared recipe: Adam (lr 1e-3 for A, 1e-4 for B), at most 15 epochs, batch size 32,
cross-entropy loss, light augmentation (horizontal flip, rotation ± 10°). The **checkpoint
kept is the one with the best validation macro-F1**. Seed 20261029, cuDNN deterministic
mode.

## Outputs

- `figshare_eval/ground_truth.csv` (`case_id`, `true_label`, `patient_id`).
- `figshare_eval/preds_*.csv` (`predicted_label` = argmax, `score_*` = softmax).
- SHA-256 of the weights, training configuration and library versions, in
  `figshare_eval/training_*.json`.
- MedVision QA report generated with `figshare_eval/config.toml`.

## Acceptance criteria

See `figshare_eval/config.toml` (C1 non-inferiority of macro-F1, margin 0.03; C2 glioma
sensitivity ≥ 0.90; C3 superiority of the glioma AUROC).
