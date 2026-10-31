# RSNA lung opacity: Faster R-CNN at 512 px vs 384 px

[日本語](README.ja.md)

MedVision QA evaluation of two lung-opacity detectors trained by the author on the
[RSNA Pneumonia Detection Challenge](https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge)
data. Training, protocol and detection metrics are in their own repository,
[cxr-pneumonia-detection](https://github.com/MousJB/cxr-pneumonia-detection); this folder
holds a copy of its MedVision QA files (same bytes, same SHA-256).

> Research project, **not a medical device**, no clinical validation. One dataset from one
> source; this result says nothing about clinical performance.

## What is compared

- **A** `frcnn-r50-fpn-512`: torchvision Faster R-CNN ResNet-50 FPN, COCO weights, input 512 px.
- **B** `frcnn-r50-fpn-384`: same model, recipe, seed and budget; input 384 px (the only change).

Criteria fixed before training (pre-registered protocol of the cxr repository):
C1 AUROC, C2 sensitivity, C3 specificity of B not inferior to A, margins 0.02, 0.05, 0.05.
Test split: 5,349 images (1,207 with opacity) of 2,290 patients, disjoint from training and
validation, evaluated once. Bootstrap by patient (2,000 resamples, seed 20261030).

MedVision QA works at image level, so each image is scored by its highest box score, mapped
so that the threshold τ chosen on validation becomes 0.5 (`predicted_label = opacity` if
the score ≥ τ). The box-level competition metric is reported in the cxr repository, not here.

## Result: SATISFIED (all three criteria)

| Image level | A, 512 px | B, 384 px | B − A [95 % CI] |
|---|---|---|---|
| AUROC | 0.8883 | 0.8889 | +0.0006 [−0.0027, +0.0038] |
| Sensitivity at τ | 0.6835 | 0.7117 | +0.0282 [+0.0084, +0.0512] |
| Specificity at τ | 0.8725 | 0.8590 | −0.0135 [−0.0202, −0.0068] |

Values from the Version Verification Records. The cxr repository's own bootstrap
(`scripts/evaluate.py`, [test_results.md](test_results.md)) gives the same point estimates
and slightly different intervals (by at most 0.002; different resampling code). It also
gives the box-level competition metric (A 0.2053, B 0.2190, B − A +0.0137 [+0.0040, +0.0238]:
non-inferior, margin 0.02). Reports:
[English](report.html), [Japanese](report.ja.html).

The specificity of B is lower (the interval excludes zero) but within the pre-registered
margin of 0.05; at the same τ = 0.80, B flags more images than A. The AUROC is unchanged.

## Files

| File | Content |
|---|---|
| `config.toml` | evaluation configuration (byte-identical to the cxr repository) |
| `config.ja.toml` | same values, free text in Japanese |
| `medvision/ground_truth.csv` | `case_id`, label, NIH patient, view, sex, age (no image) |
| `medvision/preds_r50_512.csv`, `medvision/preds_r50_384.csv` | image-level predictions of A and B |
| `report.html`, `report.ja.html` | Version Verification Records generated in the cxr repository (`reports/vvr_en.html`, `reports/vvr_ja.html` there) |
| `test_results.md` | full test tables of the cxr repository (box metrics, error analysis) |

Data: RSNA Pneumonia Detection Challenge, competition rules (non-commercial use, no
redistribution of the images). No image is included.

## Reproduce the report

```bash
python -m medvision_qa experiments/rsna_pneumonia/config.toml -o reports/rsna.html
python -m medvision_qa experiments/rsna_pneumonia/config.ja.toml -o reports/rsna.ja.html --lang ja
```

Also served by the web interface at `/demo/rsna-pneumonia`.
