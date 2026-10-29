# Evaluation configuration, acceptance criteria and metadata — v0.1

[日本語](ja/evaluation_config.md)

Status: defined in Phase 0. Reading/validation (`src/medvision_qa/config.py`) and the
decision engine (`src/medvision_qa/decision_engine.py`) **implemented in Phase 2**. The
metadata appear in the report since Phase 3. The example below is loaded as is by
`tests/test_config.py`.

File paths: **relative to the folder of the configuration file**, without leaving it.
Absolute paths and `..` are refused (protection against directory traversal). The file
must exist.

Format: **TOML** (readable, can hold comments, read by `tomllib` from the standard
library, no dependency). Unknown key → error, so that a typo cannot silently disable a
criterion.

---

## 1. Complete example

```toml
schema_version = "0.1"

[evaluation]
title = "SimpleCNN v1 vs v2 — standard test"
objective = "Check that v2 is not inferior to v1 in macro-F1."

[classes]
order = ["glioma", "meningioma", "notumor", "pituitary"]
positive = ["glioma", "meningioma", "pituitary"]   # optional; tumour vs notumor. Required for sensitivity/specificity/AUROC

[data]
ground_truth_mode = "separate_file"   # or "embedded"
ground_truth_file = "ground_truth.csv"
description = "Kaggle MRI-BT, Testing/ folder"
nature = "clinical"           # synthetic | clinical | not_provided (default)
manifest_sha256 = ""          # empty = not provided, shown as such

[versions.A]
id = "simplecnn-v1"
predictions_file = "preds_v1.csv"
code_commit = ""              # empty = not provided; never guessed
weights_sha256 = ""
preprocessing = "greyscale, p1-p99 clipping, z-score, 224×224"
description = ""

[versions.B]
id = "simplecnn-v2"
predictions_file = "preds_v2.csv"
code_commit = ""
weights_sha256 = ""
description = ""

[statistics]
confidence_level = 0.95
bootstrap_resamples = 2000
seed = 20261029               # required, no default value
probability_sum_tolerance = 1e-3

[sample_size]
status = "not_provided"       # provided | not_provided | not_applicable | based_on_data_availability
justification = ""            # required if provided or not_applicable

[[criteria]]
id = "C1"
description = "Macro-F1 of B not inferior to A, margin 0.02"
kind = "non_inferiority"
metric = "macro_f1"
margin = 0.02

[[criteria]]
id = "C2"
description = "Glioma recall of B at least 0.90"
kind = "absolute"
metric = "recall"
class = "glioma"
threshold = 0.90
```

---

## 2. Fields

### Values not provided

An empty metadata field (`""`) means **not provided**, and the report shows "Not
provided". The tool never computes or guesses a commit, a hash, a model identifier or a
provenance that was not provided.

### `data.nature`

`synthetic` shows a "synthetic data" banner at the top of the report. `clinical` means
real images, which says nothing about how representative they are. `not_provided`
(default) is shown as such.

### `[statistics]`

| Field | Rule |
|---|---|
| `confidence_level` | number strictly between 0 and 1 |
| `bootstrap_resamples` | integer ≥ 1000 (below that, percentile bounds are too unstable) |
| `seed` | integer, **required**: without a seed, no reproducibility |
| `probability_sum_tolerance` | number > 0 |

### `[sample_size]` (section 9 of the specification)

| `status` | `justification` | Shown as |
|---|---|---|
| `provided` | required (method, assumptions, parameters, reference) | the text provided |
| `not_provided` | must be empty | **Not provided** |
| `not_applicable` | required (reason) | the text provided |
| `based_on_data_availability` | optional | warning: *this is not a statistical justification* |

The actual sample size is always shown separately.

### Language of the free text

Titles, objectives and descriptions are free text: the report shows them as written.
For a report entirely in Japanese, write them in Japanese and run with `--lang ja` (see
`examples/synthetic_demo/config.ja.toml`).

---

## 3. Acceptance criteria

### Metrics allowed in a criterion (v0.1)

| `metric` | Parameter | Requires |
|---|---|---|
| `accuracy` | — | — |
| `macro_f1` | — | — |
| `precision`, `recall`, `f1` | `class` | — |
| `sensitivity`, `specificity` | — | `classes.positive` (derived binary task, see [data_format.md](data_format.md#positive-classes-derived-binary-task)) |
| `auroc` | — | `classes.positive` and scores |

Comparing AUROC between versions: paired bootstrap (Phase 2). DeLong is not implemented
in v0.1, for lack of an independent reference to validate it against (R not available).

All these metrics are "higher is better".

### Criterion types and decision rules

Every decision rests on the **two-sided confidence interval** at level
`confidence_level` (bootstrap, Phase 1/2), never on the point estimate alone. Notation:
`[L, U]` = bounds of the CI.

**`absolute`**: the metric of one version against a threshold `threshold` ∈ [0, 1].
Optional key `version = "A"` or `"B"`. Default: B if declared, otherwise A. The version
used is shown in the result.

| Condition | State |
|---|---|
| `L ≥ threshold` | `SATISFIED` |
| `U < threshold` | `NOT_SATISFIED` |
| otherwise | `INCONCLUSIVE` |

**`non_inferiority`**: difference `Δ = B − A`, margin `margin > 0`:

| Condition | State |
|---|---|
| `L(Δ) > −margin` | `SATISFIED` |
| `U(Δ) < −margin` | `NOT_SATISFIED` |
| otherwise | `INCONCLUSIVE` |

With a two-sided 95% CI, this corresponds to a one-sided test at α = 2.5%. The absence of
a significant difference **never** leads to `SATISFIED`.

**`superiority`**: difference `Δ = B − A`:

| Condition | State |
|---|---|
| `L(Δ) > 0` | `SATISFIED` |
| `U(Δ) ≤ 0` | `NOT_SATISFIED` |
| otherwise | `INCONCLUSIVE` |

**In every case**, the criterion is `INCONCLUSIVE`, with the reason, if the metric is
undefined (for example, an absent class), if required data are missing (no scores for
AUROC), if the CI cannot be computed, or if the CI has **zero width** (see
[comparison.md § 3](comparison.md#3-decision-engine)).

`non_inferiority` and `superiority` criteria require `[versions.B]`. `margin` is strictly
between 0 and 1.

### Overall aggregation

| Condition | Overall state |
|---|---|
| at least one criterion `NOT_SATISFIED` | `NOT_SATISFIED` |
| otherwise, at least one criterion `INCONCLUSIVE` | `INCONCLUSIVE` |
| every criterion `SATISFIED` | `SATISFIED` |
| no criterion defined | error: an evaluation without criteria produces no decision |

No averaging and no weighting: each criterion stays visible on its own.

---

## 4. Criteria defined before the analysis: what the tool can and cannot guarantee

The tool records the SHA-256 hash of the configuration file and the run timestamp, and
shows them in the report. It **cannot prove** that the criteria were written before the
results were known. Recommended practice: commit the configuration to git before the
first run; the report shows the hash, so a reviewer can compare it with the commit.
