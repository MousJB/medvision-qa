"""Paired comparison of two versions evaluated on the same cases (docs/comparison.md)."""

from dataclasses import dataclass

import numpy as np
from scipy.stats import binomtest

from medvision_qa.alignment import AlignedData
from medvision_qa.confidence_intervals import (BootstrapSettings, ConfidenceInterval,
                                               bootstrap_settings, run_bootstrap)
from medvision_qa.i18n import Text, msg
from medvision_qa.metrics import MetricValue, compute_metrics

DELONG_STATUS = msg("cmp.delong_status")


@dataclass(frozen=True)
class PairedDifferences:
    """Intervals of Δ = B − A, with the same resamples for A and B."""

    reference: str
    candidate: str
    settings: BootstrapSettings
    intervals: dict[str, ConfidenceInterval]


@dataclass(frozen=True)
class McNemarResult:
    """Exact McNemar test on paired correctness (correct/incorrect).

    ``only_reference_correct`` = b, ``only_candidate_correct`` = c. ``p_value`` is None
    when the test does not apply (``not_applicable_reason``).
    """

    both_correct: int
    only_reference_correct: int
    only_candidate_correct: int
    both_wrong: int
    p_value: float | None
    not_applicable_reason: Text | None
    method: Text = msg("cmp.mcnemar_method")


def _difference(a: MetricValue, b: MetricValue) -> MetricValue:
    if a.defined and b.defined:
        return MetricValue(b.value - a.value)
    details = tuple(msg("cmp.undefined_detail", version=name, reason=m.undefined_reason)
                    for name, m in (("A", a), ("B", b)) if not m.defined)
    return MetricValue(None, msg("cmp.undefined_for", details=details))


def paired_differences(data: AlignedData, reference: str, candidate: str, *, n_resamples: int,
                       confidence_level: float, seed: int) -> PairedDifferences:
    for v in (reference, candidate):
        if v not in data.y_pred:
            raise KeyError(f"Unknown version: {v!r} (available: {list(data.y_pred)}).")
    if reference == candidate:
        raise ValueError("A comparison needs two distinct versions.")
    settings, members = bootstrap_settings(data, n_resamples, confidence_level, seed)
    y_true = data.y_true
    pred_a, pred_b = data.y_pred[reference], data.y_pred[candidate]
    scores_a, scores_b = data.scores[reference], data.scores[candidate]

    def statistic(idx):
        a = compute_metrics(data.classes, y_true[idx], pred_a[idx],
                            scores_a[idx] if scores_a is not None else None)
        b = compute_metrics(data.classes, y_true[idx], pred_b[idx],
                            scores_b[idx] if scores_b is not None else None)
        return {k: _difference(a[k], b[k]) for k in a}

    return PairedDifferences(reference, candidate, settings,
                             run_bootstrap(data, settings, members, statistic))


def mcnemar(data: AlignedData, reference: str, candidate: str) -> McNemarResult:
    correct_a = data.y_pred[reference] == data.y_true
    correct_b = data.y_pred[candidate] == data.y_true
    n11 = int(np.sum(correct_a & correct_b))
    b = int(np.sum(correct_a & ~correct_b))
    c = int(np.sum(~correct_a & correct_b))
    n00 = int(np.sum(~correct_a & ~correct_b))

    reason = None
    if data.groups is not None and len(np.unique(data.groups)) < data.n_cases:
        reason = msg("cmp.mcnemar_clustered")
    elif b + c == 0:
        reason = msg("cmp.mcnemar_no_discordant")
    p_value = None if reason else float(binomtest(b, b + c, 0.5, alternative="two-sided").pvalue)
    return McNemarResult(n11, b, c, n00, p_value, reason)
