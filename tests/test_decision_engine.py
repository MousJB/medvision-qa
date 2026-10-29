import pytest

from medvision_qa.config import Criterion
from medvision_qa.confidence_intervals import ConfidenceInterval
from medvision_qa.decision_engine import (INCONCLUSIVE, NOT_SATISFIED, SATISFIED, aggregate,
                                          evaluate_criterion)
from medvision_qa.metrics import MetricValue


def ci(lower, upper, estimate=None):
    estimate = (lower + upper) / 2 if estimate is None else estimate
    return ConfidenceInterval(MetricValue(estimate), lower, upper, None, ())


UNDEFINED = ConfidenceInterval(MetricValue(None, "classe absente"), None, None, "métrique indéfinie", ())


def absolute(threshold=0.9):
    return Criterion("C1", "seuil", "absolute", "accuracy", None, threshold, None, "B")


def non_inferiority(margin=0.02):
    return Criterion("C2", "NI", "non_inferiority", "macro_f1", None, None, margin, None)


def superiority():
    return Criterion("C3", "sup", "superiority", "auroc", None, None, None, None)


@pytest.mark.parametrize("interval, state", [
    (ci(0.91, 0.95), SATISFIED),
    (ci(0.90, 0.95), SATISFIED),       # borne incluse : L ≥ seuil
    (ci(0.85, 0.89), NOT_SATISFIED),
    (ci(0.85, 0.90), INCONCLUSIVE),    # U = seuil : pas strictement en dessous
    (ci(0.88, 0.93), INCONCLUSIVE),
])
def test_absolute(interval, state):
    assert evaluate_criterion(absolute(), interval).state == state


@pytest.mark.parametrize("interval, state", [
    (ci(-0.01, 0.03), SATISFIED),
    (ci(-0.02, 0.03), INCONCLUSIVE),   # L = −marge : pas strictement au-dessus
    (ci(-0.06, -0.03), NOT_SATISFIED),
    (ci(-0.05, 0.01), INCONCLUSIVE),
])
def test_non_inferiority(interval, state):
    assert evaluate_criterion(non_inferiority(), interval).state == state


def test_non_significant_difference_is_not_non_inferiority():
    # Δ non significatif (l'IC contient 0) mais compatible avec une perte > marge :
    # l'absence de différence significative ne doit pas conclure à la non-infériorité.
    result = evaluate_criterion(non_inferiority(0.02), ci(-0.08, 0.04, estimate=-0.01))
    assert result.state == INCONCLUSIVE
    assert "ni démontrée ni exclue" in result.reason


@pytest.mark.parametrize("interval, state", [
    (ci(0.01, 0.05), SATISFIED),
    (ci(-0.03, 0.02), INCONCLUSIVE),
    (ci(-0.03, 0.0), NOT_SATISFIED),
])
def test_superiority(interval, state):
    assert evaluate_criterion(superiority(), interval).state == state


def test_undefined_interval_is_inconclusive_with_reason():
    result = evaluate_criterion(absolute(), UNDEFINED)
    assert result.state == INCONCLUSIVE and "métrique indéfinie" in result.reason


@pytest.mark.parametrize("criterion", [absolute(0.5), non_inferiority(), superiority()])
def test_zero_width_interval_never_satisfied(criterion):
    # Ex. accuracy = 1 sur tous les tirages : un IC [1, 1] ne démontre rien.
    assert evaluate_criterion(criterion, ci(1.0, 1.0)).state == INCONCLUSIVE


def test_aggregation_not_satisfied_wins():
    results = (evaluate_criterion(absolute(), ci(0.91, 0.95)),
               evaluate_criterion(non_inferiority(), ci(-0.05, 0.01)),
               evaluate_criterion(superiority(), ci(-0.03, -0.01)))
    decision = aggregate(results)
    assert decision.state == NOT_SATISFIED and "C3" in decision.reason


def test_aggregation_inconclusive_not_hidden_by_satisfied():
    results = (evaluate_criterion(absolute(), ci(0.91, 0.95)),
               evaluate_criterion(non_inferiority(), ci(-0.05, 0.01)))
    assert aggregate(results).state == INCONCLUSIVE


def test_aggregation_all_satisfied():
    results = (evaluate_criterion(absolute(), ci(0.91, 0.95)),
               evaluate_criterion(superiority(), ci(0.01, 0.02)))
    assert aggregate(results).state == SATISFIED


def test_aggregation_requires_criteria():
    with pytest.raises(ValueError):
        aggregate(())
