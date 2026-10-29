import math

import numpy as np
import pytest

from medvision_qa.alignment import AlignedData
from medvision_qa.classes import ClassSpec
from medvision_qa.comparison import mcnemar, paired_differences

SPEC = ClassSpec(("neg", "pos"), ("pos",))
STATS = dict(n_resamples=1000, confidence_level=0.95, seed=7)


def make_data(y_true, pred_a, pred_b, scores_a=None, scores_b=None, groups=None):
    y_true = np.asarray(y_true)
    return AlignedData(SPEC, "separate_file", tuple(f"c{i:04d}" for i in range(len(y_true))),
                       y_true, {"A": np.asarray(pred_a), "B": np.asarray(pred_b)},
                       {"A": scores_a, "B": scores_b},
                       None if groups is None else np.asarray(groups))


def exact_mcnemar_reference(b, c):
    """McNemar exact écrit à la main (sans scipy) : 2 × P(X ≤ min(b, c)), X ~ Bin(b + c, ½)."""
    n, k = b + c, min(b, c)
    return min(1.0, 2 * math.fsum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def with_discordant(b, c, concordant=50):
    """A seul correct sur b cas, B seul correct sur c cas, les deux corrects ailleurs."""
    n = b + c + concordant
    y = np.zeros(n, dtype=int)
    pred_a = np.zeros(n, dtype=int)
    pred_b = np.zeros(n, dtype=int)
    pred_b[:b] = 1          # B faux, A juste
    pred_a[b:b + c] = 1     # A faux, B juste
    return make_data(y, pred_a, pred_b)


@pytest.mark.parametrize("b, c", [(1, 0), (5, 2), (10, 3), (12, 12), (0, 9), (40, 25)])
def test_mcnemar_matches_closed_form(b, c):
    result = mcnemar(with_discordant(b, c), "A", "B")
    assert (result.only_reference_correct, result.only_candidate_correct) == (b, c)
    assert result.p_value == pytest.approx(exact_mcnemar_reference(b, c), rel=1e-9)


def test_mcnemar_counts_sum_to_n():
    r = mcnemar(with_discordant(4, 6, concordant=30), "A", "B")
    assert r.both_correct + r.only_reference_correct + r.only_candidate_correct + r.both_wrong == 40


def test_mcnemar_not_applicable_without_discordant_pairs():
    r = mcnemar(with_discordant(0, 0), "A", "B")
    assert r.p_value is None and "discordante" in r.not_applicable_reason


def test_mcnemar_not_applicable_with_several_cases_per_patient():
    d = with_discordant(5, 1)
    clustered = make_data(d.y_true, d.y_pred["A"], d.y_pred["B"],
                          groups=np.arange(d.n_cases) // 2)
    r = mcnemar(clustered, "A", "B")
    assert r.p_value is None and "patient" in r.not_applicable_reason


def test_mcnemar_applicable_with_one_case_per_patient():
    d = with_discordant(5, 1)
    data = make_data(d.y_true, d.y_pred["A"], d.y_pred["B"], groups=np.arange(d.n_cases))
    assert mcnemar(data, "A", "B").p_value is not None


def test_difference_direction_is_b_minus_a():
    # B corrige 30 erreurs de A : Δ accuracy = +30/200.
    d = with_discordant(0, 30, concordant=170)
    diff = paired_differences(d, "A", "B", **STATS).intervals["accuracy"]
    assert diff.estimate.value == pytest.approx(30 / 200)
    assert diff.lower > 0


def test_pairing_narrows_interval_compared_with_single_versions():
    # A et B ne diffèrent que sur 4 cas sur 400 : Δ est très précis, alors que chaque
    # accuracy prise seule est incertaine (≈ ±0,04).
    rng = np.random.default_rng(0)
    n = 400
    y = rng.integers(0, 2, n)
    pred_a = np.where(rng.random(n) < 0.75, y, 1 - y)
    pred_b = pred_a.copy()
    flip = np.flatnonzero(pred_a != y)[:4]
    pred_b[flip] = y[flip]
    diff = paired_differences(make_data(y, pred_a, pred_b), "A", "B", **STATS).intervals["accuracy"]
    assert diff.upper - diff.lower < 0.03


def test_identical_versions_give_zero_width_difference():
    d = with_discordant(0, 0)
    diff = paired_differences(d, "A", "B", **STATS).intervals["accuracy"]
    assert diff.estimate.value == 0 and diff.zero_width


def test_difference_undefined_when_metric_undefined_for_one_version():
    d = with_discordant(3, 3)  # aucun positif dans les vérités terrain
    diff = paired_differences(d, "A", "B", **STATS).intervals["sensitivity"]
    assert not diff.defined and "A :" in diff.estimate.undefined_reason


def test_auroc_difference_uses_scores_of_each_version():
    rng = np.random.default_rng(1)
    n = 300
    y = rng.integers(0, 2, n)
    good = np.clip(0.5 + 0.35 * (2 * y - 1) + rng.normal(0, 0.15, n), 0, 1)
    poor = np.clip(0.5 + 0.05 * (2 * y - 1) + rng.normal(0, 0.15, n), 0, 1)
    to_scores = lambda p: np.column_stack([1 - p, p])  # noqa: E731
    d = make_data(y, (poor > 0.5).astype(int), (good > 0.5).astype(int), to_scores(poor), to_scores(good))
    diff = paired_differences(d, "A", "B", **STATS).intervals["auroc"]
    assert diff.lower > 0.2


def test_auroc_difference_undefined_without_scores():
    diff = paired_differences(with_discordant(3, 3), "A", "B", **STATS).intervals["auroc"]
    assert not diff.defined


def test_same_version_rejected():
    with pytest.raises(ValueError):
        paired_differences(with_discordant(1, 1), "A", "A", **STATS)
