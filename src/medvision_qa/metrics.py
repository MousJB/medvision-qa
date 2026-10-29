"""Métriques de classification (docs/metrics.md).

Une métrique non calculable est renvoyée comme indéfinie avec sa raison ; elle n'est
jamais remplacée par 0 ou par une autre valeur.
"""

from dataclasses import dataclass

import numpy as np
from scipy.stats import rankdata

from medvision_qa.classes import ClassSpec

PER_CLASS_METRICS = ("precision", "recall", "f1")

DEFINITIONS = {
    "accuracy": "Proportion de cas dont predicted_label = true_label.",
    "precision": "TP / (TP + FP) pour la classe, un contre tous. Indéfinie si la classe n'est jamais prédite.",
    "recall": "TP / (TP + FN) pour la classe, un contre tous. Indéfini si la classe est absente des vérités terrain.",
    "f1": "2·TP / (2·TP + FP + FN) pour la classe. Indéfini si la classe est absente des vérités terrain et des prédictions.",
    "macro_f1": "Moyenne non pondérée des F1 par classe, sur toutes les classes déclarées. Indéfinie si un F1 est indéfini.",
    "sensitivity": "Tâche binaire dérivée : TP / (TP + FN). Indéfinie sans classe positive déclarée ou sans cas positif.",
    "specificity": "Tâche binaire dérivée : TN / (TN + FP). Indéfinie sans classe positive déclarée ou sans cas négatif.",
    "auroc": ("Tâche binaire dérivée, score positif = somme des scores des classes positives ; "
              "statistique de Mann-Whitney, ex æquo comptés 1/2. Indéfinie sans scores, sans classe "
              "positive déclarée, ou si une seule des deux classes binaires est présente."),
}


@dataclass(frozen=True)
class MetricValue:
    value: float | None
    undefined_reason: str | None = None

    def __post_init__(self):
        if (self.value is None) == (self.undefined_reason is None):
            raise ValueError("Une métrique a soit une valeur, soit une raison d'être indéfinie.")

    @property
    def defined(self) -> bool:
        return self.value is not None


def _defined(value) -> MetricValue:
    return MetricValue(float(value))


def _undefined(reason) -> MetricValue:
    return MetricValue(None, reason)


def metric_key(metric: str, class_name: str | None = None) -> str:
    return f"{metric}[{class_name}]" if class_name is not None else metric


def metric_keys(classes: ClassSpec) -> tuple[str, ...]:
    per_class = tuple(metric_key(m, c) for m in PER_CLASS_METRICS for c in classes.order)
    return ("accuracy", "macro_f1") + per_class + ("sensitivity", "specificity", "auroc")


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    """Matrice (k, k) : lignes = vérité, colonnes = prédiction, dans l'ordre des classes."""
    return np.bincount(y_true * n_classes + y_pred, minlength=n_classes * n_classes).reshape(
        n_classes, n_classes)


def _ratio(numerator, denominator, reason) -> MetricValue:
    return _defined(numerator / denominator) if denominator > 0 else _undefined(reason)


def auroc(y_binary: np.ndarray, score: np.ndarray) -> MetricValue:
    n_pos = int(y_binary.sum())
    n_neg = len(y_binary) - n_pos
    if n_pos == 0 or n_neg == 0:
        return _undefined("une seule classe binaire présente (positifs et négatifs requis)")
    ranks = rankdata(score)  # rangs moyens en cas d'ex æquo
    u = ranks[y_binary].sum() - n_pos * (n_pos + 1) / 2
    return _defined(u / (n_pos * n_neg))


def compute_metrics(classes: ClassSpec, y_true: np.ndarray, y_pred: np.ndarray,
                    scores: np.ndarray | None) -> dict[str, MetricValue]:
    """Calcule toutes les métriques de ``metric_keys(classes)``, dans cet ordre."""
    k = len(classes.order)
    cm = confusion_matrix(y_true, y_pred, k)
    tp = np.diag(cm)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp

    results = {"accuracy": _defined(tp.sum() / cm.sum())}
    f1_values = []
    for i, c in enumerate(classes.order):
        results[metric_key("precision", c)] = _ratio(tp[i], tp[i] + fp[i], f"classe {c!r} jamais prédite")
        results[metric_key("recall", c)] = _ratio(tp[i], tp[i] + fn[i],
                                                  f"classe {c!r} absente des vérités terrain")
        f1 = _ratio(2 * tp[i], 2 * tp[i] + fp[i] + fn[i],
                    f"classe {c!r} absente des vérités terrain et des prédictions")
        results[metric_key("f1", c)] = f1
        f1_values.append(f1)

    undefined_f1 = [c for c, f in zip(classes.order, f1_values) if not f.defined]
    results["macro_f1"] = (_undefined(f"F1 indéfini pour {undefined_f1}") if undefined_f1
                           else _defined(np.mean([f.value for f in f1_values])))

    if not classes.positive:
        reason = "aucune classe positive déclarée"
        for key in ("sensitivity", "specificity", "auroc"):
            results[key] = _undefined(reason)
        return {k: results[k] for k in metric_keys(classes)}

    positive = np.array(classes.positive_indices)
    true_pos = np.isin(y_true, positive)
    pred_pos = np.isin(y_pred, positive)
    results["sensitivity"] = _ratio(np.sum(true_pos & pred_pos), true_pos.sum(),
                                    "aucun cas positif dans les vérités terrain")
    results["specificity"] = _ratio(np.sum(~true_pos & ~pred_pos), (~true_pos).sum(),
                                    "aucun cas négatif dans les vérités terrain")
    results["auroc"] = (auroc(true_pos, scores[:, positive].sum(axis=1)) if scores is not None
                        else _undefined("scores non fournis"))
    return {k: results[k] for k in metric_keys(classes)}
