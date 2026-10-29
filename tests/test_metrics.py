"""Metrics: values computed by hand, then compared with scikit-learn (independent reference)."""

import numpy as np
import pytest
from sklearn import metrics as skm

from medvision_qa.classes import ClassSpec
from medvision_qa.i18n import raw
from medvision_qa.metrics import (DEFINITIONS, MetricValue, auroc, compute_metrics,
                                  confusion_matrix, metric_keys)

ABC = ClassSpec(("a", "b", "c"))


def test_hand_computed_example():
    # truth: a a a b b c; prediction: a a b b c c
    y_true = np.array([0, 0, 0, 1, 1, 2])
    y_pred = np.array([0, 0, 1, 1, 2, 2])
    cm = confusion_matrix(y_true, y_pred, 3)
    assert cm.tolist() == [[2, 1, 0], [0, 1, 1], [0, 0, 1]]

    m = compute_metrics(ABC, y_true, y_pred, None)
    assert m["accuracy"].value == pytest.approx(4 / 6)
    assert m["precision[a]"].value == pytest.approx(1.0)
    assert m["recall[a]"].value == pytest.approx(2 / 3)
    assert m["f1[a]"].value == pytest.approx(0.8)
    assert m["precision[b]"].value == pytest.approx(0.5)
    assert m["recall[b]"].value == pytest.approx(0.5)
    assert m["f1[c]"].value == pytest.approx(2 / 3)
    assert m["macro_f1"].value == pytest.approx((0.8 + 0.5 + 2 / 3) / 3)


def test_all_keys_present_and_documented():
    m = compute_metrics(ABC, np.array([0, 1, 2]), np.array([0, 1, 2]), None)
    assert tuple(m) == metric_keys(ABC)
    for key in m:
        assert key.split("[")[0] in DEFINITIONS


@pytest.mark.parametrize("seed", range(5))
def test_matches_sklearn_on_random_data(seed):
    rng = np.random.default_rng(seed)
    k, n = 4, 300
    spec = ClassSpec(("w", "x", "y", "z"), ("w", "x"))
    y_true = rng.integers(0, k, n)
    y_pred = np.where(rng.random(n) < 0.6, y_true, rng.integers(0, k, n))
    scores = rng.dirichlet(np.ones(k), n)

    m = compute_metrics(spec, y_true, y_pred, scores)
    labels = list(range(k))
    np.testing.assert_array_equal(confusion_matrix(y_true, y_pred, k),
                                  skm.confusion_matrix(y_true, y_pred, labels=labels))
    assert m["accuracy"].value == pytest.approx(skm.accuracy_score(y_true, y_pred))
    p, r, f, _ = skm.precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=np.nan)
    for i, c in enumerate(spec.order):
        assert m[f"precision[{c}]"].value == pytest.approx(p[i])
        assert m[f"recall[{c}]"].value == pytest.approx(r[i])
        assert m[f"f1[{c}]"].value == pytest.approx(f[i])
    assert m["macro_f1"].value == pytest.approx(skm.f1_score(y_true, y_pred, average="macro"))

    true_bin = np.isin(y_true, [0, 1])
    pred_bin = np.isin(y_pred, [0, 1])
    assert m["sensitivity"].value == pytest.approx(skm.recall_score(true_bin, pred_bin))
    assert m["specificity"].value == pytest.approx(skm.recall_score(~true_bin, ~pred_bin))
    assert m["auroc"].value == pytest.approx(skm.roc_auc_score(true_bin, scores[:, :2].sum(axis=1)))


def test_class_never_predicted_precision_undefined_not_zero():
    m = compute_metrics(ABC, np.array([0, 1, 2]), np.array([0, 1, 1]), None)
    assert not m["precision[c]"].defined
    assert m["precision[c]"].undefined_reason.key == "metric.never_predicted"
    assert m["recall[c]"].value == 0.0
    assert m["f1[c]"].value == 0.0  # 2TP/(2TP+FP+FN) = 0/1: defined


def test_class_absent_everywhere_makes_macro_f1_undefined():
    m = compute_metrics(ABC, np.array([0, 1, 0]), np.array([0, 1, 1]), None)
    assert not m["recall[c]"].defined
    assert not m["f1[c]"].defined
    assert not m["macro_f1"].defined
    assert "['c']" in str(m["macro_f1"].undefined_reason)


def test_binary_metrics_undefined_without_positive_class():
    m = compute_metrics(ABC, np.array([0, 1, 2]), np.array([0, 1, 2]), np.full((3, 3), 1 / 3))
    for key in ("sensitivity", "specificity", "auroc"):
        assert str(m[key].undefined_reason) == "no positive class declared"


def test_auroc_undefined_without_scores():
    spec = ClassSpec(("a", "b", "c"), ("a",))
    m = compute_metrics(spec, np.array([0, 1, 2]), np.array([0, 1, 2]), None)
    assert str(m["auroc"].undefined_reason) == "scores not provided"
    assert m["sensitivity"].value == 1.0


def test_sensitivity_undefined_without_positive_cases():
    spec = ClassSpec(("a", "b", "c"), ("a",))
    m = compute_metrics(spec, np.array([1, 2]), np.array([0, 2]), np.array([[.5, .5, 0], [0, 0, 1]]))
    assert not m["sensitivity"].defined
    assert m["specificity"].value == 0.5
    assert not m["auroc"].defined


def test_auroc_hand_computed_with_ties():
    # positives: 0.8, 0.5; negatives: 0.5, 0.2 → pairs: (0.8>0.5)(0.8>0.2)(0.5=0.5)(0.5>0.2) = 3.5/4
    y = np.array([True, True, False, False])
    s = np.array([0.8, 0.5, 0.5, 0.2])
    assert auroc(y, s).value == pytest.approx(0.875)


def test_metric_value_invariant():
    with pytest.raises(ValueError):
        MetricValue(None, None)
    with pytest.raises(ValueError):
        MetricValue(0.5, raw("reason"))
