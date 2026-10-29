"""Intervalles de confiance par bootstrap percentile (docs/metrics.md § 3).

Unité de rééchantillonnage : le patient si ``patient_id`` est fourni (bootstrap par
grappes), sinon le cas. Un intervalle n'est produit que si la métrique est définie sur
l'échantillon complet et dans chaque rééchantillon.
"""

import math
from dataclasses import dataclass

import numpy as np

from medvision_qa.alignment import AlignedData
from medvision_qa.classes import ConfigError
from medvision_qa.metrics import MetricValue, compute_metrics, metric_keys

MIN_RESAMPLES = 1000
SMALL_SAMPLE_UNITS = 30
METHOD = "percentile"
QUANTILE_METHOD = "linear"


@dataclass(frozen=True)
class BootstrapSettings:
    n_resamples: int
    confidence_level: float
    seed: int
    unit: str  # "case" ou "patient"
    n_units: int
    method: str = METHOD
    quantile_method: str = QUANTILE_METHOD


@dataclass(frozen=True)
class ConfidenceInterval:
    estimate: MetricValue
    lower: float | None
    upper: float | None
    undefined_reason: str | None
    warnings: tuple[str, ...]

    @property
    def defined(self) -> bool:
        return self.lower is not None


@dataclass(frozen=True)
class BootstrapResult:
    version: str
    settings: BootstrapSettings
    intervals: dict[str, ConfidenceInterval]


def validate_settings(n_resamples, confidence_level, seed):
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int) or n_resamples < MIN_RESAMPLES:
        raise ConfigError(f"bootstrap_resamples doit être un entier ≥ {MIN_RESAMPLES}.")
    if (isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float))
            or not math.isfinite(confidence_level) or not 0 < confidence_level < 1):
        raise ConfigError("confidence_level doit être un réel dans ]0, 1[.")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ConfigError("seed doit être un entier ≥ 0 (obligatoire pour la reproductibilité).")


def group_members(groups: np.ndarray) -> list[np.ndarray]:
    """Indices des cas de chaque patient."""
    order = np.argsort(groups, kind="stable")
    boundaries = np.flatnonzero(np.diff(groups[order])) + 1
    return np.split(order, boundaries)


def resample_indices(rng: np.random.Generator, n_cases: int,
                     members: list[np.ndarray] | None) -> np.ndarray:
    """Tire des unités avec remise ; avec ``members``, renvoie tous les cas des patients tirés."""
    if members is None:
        return rng.integers(0, n_cases, size=n_cases)
    drawn = rng.integers(0, len(members), size=len(members))
    return np.concatenate([members[g] for g in drawn])


def bootstrap_metrics(data: AlignedData, version: str, *, n_resamples: int,
                      confidence_level: float, seed: int) -> BootstrapResult:
    validate_settings(n_resamples, confidence_level, seed)
    if version not in data.y_pred:
        raise KeyError(f"Version inconnue : {version!r} (disponibles : {list(data.y_pred)}).")

    classes = data.classes
    y_true, y_pred, scores = data.y_true, data.y_pred[version], data.scores[version]
    unit = "patient" if data.groups is not None else "case"
    members = group_members(data.groups) if data.groups is not None else None
    n_units = len(members) if members is not None else data.n_cases
    settings = BootstrapSettings(n_resamples, float(confidence_level), seed, unit, n_units)

    estimates = compute_metrics(classes, y_true, y_pred, scores)
    keys = metric_keys(classes)
    samples = {k: np.empty(n_resamples) for k in keys}
    undefined_counts = dict.fromkeys(keys, 0)

    rng = np.random.default_rng(seed)
    for r in range(n_resamples):
        idx = resample_indices(rng, data.n_cases, members)
        values = compute_metrics(classes, y_true[idx], y_pred[idx],
                                 scores[idx] if scores is not None else None)
        for k in keys:
            if values[k].defined:
                samples[k][r] = values[k].value
            else:
                undefined_counts[k] += 1

    alpha = 1 - confidence_level
    intervals = {}
    for k in keys:
        estimate = estimates[k]
        if not estimate.defined:
            intervals[k] = ConfidenceInterval(estimate, None, None,
                                              f"métrique indéfinie : {estimate.undefined_reason}", ())
            continue
        if undefined_counts[k]:
            intervals[k] = ConfidenceInterval(
                estimate, None, None,
                f"métrique indéfinie dans {undefined_counts[k]}/{n_resamples} rééchantillonnages ; "
                "les écarter biaiserait l'intervalle", ())
            continue
        lower, upper = np.quantile(samples[k], [alpha / 2, 1 - alpha / 2], method=QUANTILE_METHOD)
        warnings = []
        if lower == upper:
            warnings.append("intervalle de largeur nulle : le bootstrap percentile sous-estime "
                            "l'incertitude quand la métrique est constante (par ex. à sa borne 0 ou 1)")
        if n_units < SMALL_SAMPLE_UNITS:
            warnings.append(f"{n_units} unité(s) de rééchantillonnage (< {SMALL_SAMPLE_UNITS}) : "
                            "couverture du bootstrap percentile non garantie")
        intervals[k] = ConfidenceInterval(estimate, float(lower), float(upper), None, tuple(warnings))

    return BootstrapResult(version, settings, intervals)
