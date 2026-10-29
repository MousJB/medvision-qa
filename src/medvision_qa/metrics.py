"""Classification metrics (docs/metrics.md).

A metric that cannot be computed is returned as undefined, with its reason; it is never
replaced by 0 or by any other value.
"""

from dataclasses import dataclass

import numpy as np
from scipy.stats import rankdata

from medvision_qa.classes import ClassSpec
from medvision_qa.i18n import Text, msg

PER_CLASS_METRICS = ("precision", "recall", "f1")

DEFINITIONS = {name: msg(f"def.{name}") for name in
               ("accuracy", "precision", "recall", "f1", "macro_f1", "sensitivity", "specificity", "auroc")}


@dataclass(frozen=True)
class MetricValue:
    value: float | None
    undefined_reason: Text | None = None

    def __post_init__(self):
        if (self.value is None) == (self.undefined_reason is None):
            raise ValueError("A metric has either a value or a reason for being undefined.")

    @property
    def defined(self) -> bool:
        return self.value is not None


def _defined(value) -> MetricValue:
    return MetricValue(float(value))


def _undefined(reason: Text) -> MetricValue:
    return MetricValue(None, reason)


def metric_key(metric: str, class_name: str | None = None) -> str:
    return f"{metric}[{class_name}]" if class_name is not None else metric


def metric_keys(classes: ClassSpec) -> tuple[str, ...]:
    per_class = tuple(metric_key(m, c) for m in PER_CLASS_METRICS for c in classes.order)
    return ("accuracy", "macro_f1") + per_class + ("sensitivity", "specificity", "auroc")


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    """(k, k) matrix: rows = ground truth, columns = prediction, in class order."""
    return np.bincount(y_true * n_classes + y_pred, minlength=n_classes * n_classes).reshape(
        n_classes, n_classes)


def _ratio(numerator, denominator, reason: Text) -> MetricValue:
    return _defined(numerator / denominator) if denominator > 0 else _undefined(reason)


def auroc(y_binary: np.ndarray, score: np.ndarray) -> MetricValue:
    n_pos = int(y_binary.sum())
    n_neg = len(y_binary) - n_pos
    if n_pos == 0 or n_neg == 0:
        return _undefined(msg("metric.single_binary_class"))
    ranks = rankdata(score)  # mean ranks for ties
    u = ranks[y_binary].sum() - n_pos * (n_pos + 1) / 2
    return _defined(u / (n_pos * n_neg))


def compute_metrics(classes: ClassSpec, y_true: np.ndarray, y_pred: np.ndarray,
                    scores: np.ndarray | None) -> dict[str, MetricValue]:
    """Computes every metric of ``metric_keys(classes)``, in that order."""
    k = len(classes.order)
    cm = confusion_matrix(y_true, y_pred, k)
    tp = np.diag(cm)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp

    results = {"accuracy": _defined(tp.sum() / cm.sum())}
    f1_values = []
    for i, c in enumerate(classes.order):
        results[metric_key("precision", c)] = _ratio(tp[i], tp[i] + fp[i],
                                                     msg("metric.never_predicted", cls=repr(c)))
        results[metric_key("recall", c)] = _ratio(tp[i], tp[i] + fn[i],
                                                  msg("metric.absent_from_truth", cls=repr(c)))
        f1 = _ratio(2 * tp[i], 2 * tp[i] + fp[i] + fn[i], msg("metric.absent_everywhere", cls=repr(c)))
        results[metric_key("f1", c)] = f1
        f1_values.append(f1)

    undefined_f1 = [c for c, f in zip(classes.order, f1_values) if not f.defined]
    results["macro_f1"] = (_undefined(msg("metric.f1_undefined", classes=str(undefined_f1))) if undefined_f1
                           else _defined(np.mean([f.value for f in f1_values])))

    if not classes.positive:
        reason = msg("metric.no_positive_class")
        for key in ("sensitivity", "specificity", "auroc"):
            results[key] = _undefined(reason)
        return {k: results[k] for k in metric_keys(classes)}

    positive = np.array(classes.positive_indices)
    true_pos = np.isin(y_true, positive)
    pred_pos = np.isin(y_pred, positive)
    results["sensitivity"] = _ratio(np.sum(true_pos & pred_pos), true_pos.sum(),
                                    msg("metric.no_positive_case"))
    results["specificity"] = _ratio(np.sum(~true_pos & ~pred_pos), (~true_pos).sum(),
                                    msg("metric.no_negative_case"))
    results["auroc"] = (auroc(true_pos, scores[:, positive].sum(axis=1)) if scores is not None
                        else _undefined(msg("metric.no_scores")))
    return {k: results[k] for k in metric_keys(classes)}
