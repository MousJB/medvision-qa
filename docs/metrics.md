# Metrics and confidence intervals — v0.1

[日本語](ja/metrics.md)

Implementation: `src/medvision_qa/metrics.py`, `src/medvision_qa/confidence_intervals.py`.
Validated against scikit-learn (independent reference) in `tests/test_metrics.py`.

## 1. Conventions

- Confusion matrix: rows = ground truth, columns = prediction, in the order of
  `classes.order`.
- Per-class metrics are **one-vs-rest**. TP, FP and FN are read from the confusion matrix.
- A metric that cannot be computed is **undefined, with a reason**. It is never replaced
  by 0, by NaN or by any other value.
- Metric key: `accuracy`, `macro_f1`, `precision[<class>]`, `recall[<class>]`,
  `f1[<class>]`, `sensitivity`, `specificity`, `auroc`.

## 2. Definitions and undefined cases

| Metric | Definition | Undefined if |
|---|---|---|
| `accuracy` | correct cases / cases | never (a non-empty file is guaranteed) |
| `precision[c]` | TP / (TP + FP) | `c` is never predicted |
| `recall[c]` | TP / (TP + FN) | `c` is absent from the ground truth |
| `f1[c]` | 2·TP / (2·TP + FP + FN) | `c` is absent from the ground truth **and** from the predictions |
| `macro_f1` | unweighted mean of `f1[c]` over **all** declared classes | any `f1[c]` is undefined (no class is silently dropped) |
| `sensitivity` | TP / (TP + FN), derived binary task | no positive class, or no positive case |
| `specificity` | TN / (TN + FP), derived binary task | no positive class, or no negative case |
| `auroc` | Mann-Whitney on the positive score; ties counted as ½ | no positive class, no scores, or only one binary class present |

Note on `f1[c]`: the formula 2·TP / (2·TP + FP + FN) gives 0 when the class is present
but never correctly predicted, even if precision is undefined. This matches scikit-learn
with `zero_division` (tested).

Derived binary task (see [data_format.md](data_format.md#positive-classes-derived-binary-task)):
the binary prediction comes from `predicted_label` (no new threshold), and the positive
score is the sum of the scores of the positive classes.

## 3. Confidence intervals

| Parameter | Value |
|---|---|
| Method | **percentile** bootstrap, two-sided |
| Quantiles | `numpy.quantile(..., method="linear")` |
| Resamples | ≥ 1000 (`bootstrap_resamples` parameter) |
| Seed | required; generator `numpy.random.default_rng(seed)` |
| Unit | **patient** if `patient_id` is provided (every case of a drawn patient is included), otherwise **case** |
| Case order | sorted by `case_id`: the result does not depend on the row order of the files |

All these parameters are recorded in `BootstrapSettings`.

### When no interval is produced

- The metric is undefined on the full sample.
- The metric is undefined in **at least one** resample, for example a rare class absent
  from a draw. Discarding those draws would condition the interval and make it too
  optimistic. The interval is therefore declared not computable, with the number of
  draws concerned.

### Warnings attached to an interval

- **Zero width**: the metric is constant across all draws (e.g. accuracy = 1). The
  percentile bootstrap then does not reflect the real uncertainty.
- **Fewer than 30 resampling units**: percentile bootstrap coverage is not guaranteed.
  The threshold of 30 is a convention, not a guarantee.

## 4. Limits

- Without `patient_id`, the interval assumes independent cases. If several images come
  from the same patient, it is **too narrow** (`tests/test_confidence_intervals.py` shows
  a gap of more than ×2 on a synthetic example).
- The percentile bootstrap can have coverage below the nominal level for small samples
  or for metrics close to 0 or 1. BCa or Wilson methods are not implemented in v0.1.
- A wide interval is not proof of no difference. Comparisons between versions (paired
  bootstrap) and decisions are described in [comparison.md](comparison.md).
- No multiclass macro-AUROC in v0.1: only the AUROC of the derived binary task is
  computed.
