"""Comparaison appariée de deux versions évaluées sur les mêmes cas (docs/comparison.md)."""

from dataclasses import dataclass

import numpy as np
from scipy.stats import binomtest

from medvision_qa.alignment import AlignedData
from medvision_qa.confidence_intervals import (BootstrapSettings, ConfidenceInterval,
                                               bootstrap_settings, run_bootstrap)
from medvision_qa.metrics import MetricValue, compute_metrics

DELONG_STATUS = ("non implémenté : aucune référence indépendante (R/pROC) disponible pour le "
                 "valider ; la différence d'AUROC est estimée par bootstrap apparié")


@dataclass(frozen=True)
class PairedDifferences:
    """Intervalles de Δ = B − A, avec les mêmes rééchantillonnages pour A et B."""

    reference: str
    candidate: str
    settings: BootstrapSettings
    intervals: dict[str, ConfidenceInterval]


@dataclass(frozen=True)
class McNemarResult:
    """Test exact de McNemar sur la justesse (correct/incorrect) appariée.

    ``only_reference_correct`` = b, ``only_candidate_correct`` = c. ``p_value`` est None si
    le test n'est pas applicable (``not_applicable_reason``).
    """

    both_correct: int
    only_reference_correct: int
    only_candidate_correct: int
    both_wrong: int
    p_value: float | None
    not_applicable_reason: str | None
    method: str = "McNemar exact conditionnel (binomial bilatéral sur les paires discordantes)"


def _difference(a: MetricValue, b: MetricValue) -> MetricValue:
    if a.defined and b.defined:
        return MetricValue(b.value - a.value)
    reasons = [f"{name} : {m.undefined_reason}" for name, m in (("A", a), ("B", b)) if not m.defined]
    return MetricValue(None, "métrique indéfinie pour " + " ; ".join(reasons))


def paired_differences(data: AlignedData, reference: str, candidate: str, *, n_resamples: int,
                       confidence_level: float, seed: int) -> PairedDifferences:
    for v in (reference, candidate):
        if v not in data.y_pred:
            raise KeyError(f"Version inconnue : {v!r} (disponibles : {list(data.y_pred)}).")
    if reference == candidate:
        raise ValueError("La comparaison exige deux versions distinctes.")
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
        reason = ("plusieurs cas par patient : les paires ne sont pas indépendantes, hypothèse "
                  "du test de McNemar non satisfaite")
    elif b + c == 0:
        reason = "aucune paire discordante : le test ne contient aucune information"
    p_value = None if reason else float(binomtest(b, b + c, 0.5, alternative="two-sided").pvalue)
    return McNemarResult(n11, b, c, n00, p_value, reason)

