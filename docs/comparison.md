# Comparing two versions — v0.1

[日本語](ja/comparison.md)

Implementation: `src/medvision_qa/comparison.py`, `src/medvision_qa/decision_engine.py`,
`src/medvision_qa/evaluation.py`. Tests: `tests/test_comparison.py`,
`tests/test_decision_engine.py`, `tests/test_evaluation.py`.

Prerequisite: both versions are evaluated on **exactly the same cases** (checked by the
alignment, see [data_format.md](data_format.md#6-case-alignment)).

## 1. Paired bootstrap differences

For each metric of [metrics.md](metrics.md), Δ = B − A (positive = B better).

- In each draw, **the same indices** of cases (or patients) are used for A and for B.
  This is what exploits the pairing: the correlation between A and B reduces the
  uncertainty on Δ. One test shows a CI of Δ narrower than 0.03, whereas each accuracy
  on its own (≈ 0.75 on 400 cases) has an uncertainty of about ±0.04.
- Method, seed, unit and undefined-value rules are those of
  [metrics.md § 3](metrics.md#3-confidence-intervals). Δ is undefined as soon as the
  metric is undefined for A or for B.
- **AUROC**: the AUROC difference is estimated this way. **DeLong is not implemented**,
  for lack of an independent reference (R/pROC) to validate it. This status is recorded
  in every result (`EvaluationResult.delong_status`).

## 2. McNemar test (informative)

- Works on paired **correctness**: each case is correct or incorrect for A and for B.
  b = only A correct, c = only B correct.
- **Exact conditional** variant: two-sided binomial test of b among b + c, p = ½
  (`scipy.stats.binomtest`). It was checked against the closed form 2·P(X ≤ min(b, c)),
  written by hand in the tests. The exact variant was chosen because it stays valid with
  few discordant pairs, unlike the χ² approximation.
- **Not applicable**, with the reason, if:
  - several cases belong to the same patient: the pairs are not independent;
  - no pair is discordant (b + c = 0).
- McNemar is **not used in decisions**: those rest on the CIs (§ 3). A high p-value
  proves neither equivalence nor the absence of regression, and a low p-value does not
  measure the practical or clinical importance of the difference.

## 3. Decision engine

Rules: [evaluation_config.md § 3](evaluation_config.md#3-acceptance-criteria). The
implementation adds one rule of caution:

- a **zero-width CI** (metric constant across all draws, e.g. accuracy = 1, or A and B
  identical on every case) gives `INCONCLUSIVE`, never `SATISFIED`. The percentile
  bootstrap does not measure the uncertainty in that case.

Each criterion keeps its CI, the quantity compared (e.g. `macro_f1 (B − A)`) and a
readable reason (e.g. `CI [-0.0412, 0.0187] contains −margin (-0.0300); non-inferiority is
neither shown nor ruled out`). The reason is stored as a message key with its parameters,
so it can be shown in English or Japanese.

## 4. Traceability of a run

`run_evaluation(config)` records: run identifier (UUID4), UTC timestamp, Python version,
versions of medvision-qa, numpy, scipy, scikit-learn and jinja2, SHA-256 of the
configuration and of each CSV, checks run per file, bootstrap parameters, confusion
matrices.

Two runs of the same configuration give identical intervals and decisions (tested). Only
the identifier and the timestamp change.

## 5. Limits

- Δ is an absolute difference of the metric. No odds ratio or relative difference.
- The paired bootstrap inherits the limits of the percentile bootstrap (small samples,
  metrics close to the bounds).
- Criteria are evaluated independently, without multiplicity correction. The
  aggregation rule (every criterion `SATISFIED` for an overall `SATISFIED`) is
  conservative, but with many criteria the probability of a chance `NOT_SATISFIED` grows.
- The tool cannot prove that the criteria were fixed before the analysis (see
  [evaluation_config.md § 4](evaluation_config.md#4-criteria-defined-before-the-analysis-what-the-tool-can-and-cannot-guarantee)).
