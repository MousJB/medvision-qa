"""Intervalles de confiance par bootstrap percentile (docs/metrics.md § 3).

Unité de rééchantillonnage : le patient si ``patient_id`` est fourni (bootstrap par
grappes), sinon le cas. Un intervalle n'est produit que si la métrique est définie sur
l'échantillon complet et dans chaque rééchantillon.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from medvision_qa.alignment import AlignedData
from medvision_qa.classes import ConfigError
from medvision_qa.metrics import MetricValue, compute_metrics

MIN_RESAMPLES = 1000
SMALL_SAMPLE_UNITS = 30
METHOD = "percentile"
QUANTILE_METHOD = "linear"
ZERO_WIDTH_WARNING = ("intervalle de largeur nulle : le bootstrap percentile sous-estime "
                      "l'incertitude quand la métrique est constante (par ex. à sa borne 0 ou 1)")


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

    @property
    def zero_width(self) -> bool:
        return self.defined and self.lower == self.upper


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


def bootstrap_settings(data: AlignedData, n_resamples: int, confidence_level: float,
                       seed: int) -> tuple[BootstrapSettings, list[np.ndarray] | None]:
    validate_settings(n_resamples, confidence_level, seed)
    members = group_members(data.groups) if data.groups is not None else None
    unit = "patient" if members is not None else "case"
    n_units = len(members) if members is not None else data.n_cases
    return BootstrapSettings(n_resamples, float(confidence_level), seed, unit, n_units), members


def run_bootstrap(data: AlignedData, settings: BootstrapSettings, members,
                  statistic: Callable[[np.ndarray], dict[str, MetricValue]]) -> dict[str, ConfidenceInterval]:
    """Applique ``statistic`` (indices de cas → métriques) à l'échantillon complet puis à chaque
    rééchantillonnage, et construit un intervalle percentile par clé."""
    estimates = statistic(np.arange(data.n_cases))
    samples = {k: np.empty(settings.n_resamples) for k in estimates}
    undefined_counts = dict.fromkeys(estimates, 0)

    rng = np.random.default_rng(settings.seed)
    for r in range(settings.n_resamples):
        values = statistic(resample_indices(rng, data.n_cases, members))
        for k in estimates:
            if values[k].defined:
                samples[k][r] = values[k].value
            else:
                undefined_counts[k] += 1

    return {k: _interval(estimates[k], samples[k], undefined_counts[k], settings) for k in estimates}


def _interval(estimate: MetricValue, samples: np.ndarray, undefined_count: int,
              settings: BootstrapSettings) -> ConfidenceInterval:
    if not estimate.defined:
        return ConfidenceInterval(estimate, None, None,
                                  f"métrique indéfinie : {estimate.undefined_reason}", ())
    if undefined_count:
        return ConfidenceInterval(
            estimate, None, None,
            f"métrique indéfinie dans {undefined_count}/{settings.n_resamples} rééchantillonnages ; "
            "les écarter biaiserait l'intervalle", ())
    alpha = 1 - settings.confidence_level
    lower, upper = np.quantile(samples, [alpha / 2, 1 - alpha / 2], method=QUANTILE_METHOD)
    warnings = []
    if lower == upper:
        warnings.append(ZERO_WIDTH_WARNING)
    if settings.n_units < SMALL_SAMPLE_UNITS:
        warnings.append(f"{settings.n_units} unité(s) de rééchantillonnage (< {SMALL_SAMPLE_UNITS}) : "
                        "couverture du bootstrap percentile non garantie")
    return ConfidenceInterval(estimate, float(lower), float(upper), None, tuple(warnings))


def bootstrap_metrics(data: AlignedData, version: str, *, n_resamples: int,
                      confidence_level: float, seed: int) -> BootstrapResult:
    """Intervalles de confiance de toutes les métriques d'une version."""
    if version not in data.y_pred:
        raise KeyError(f"Version inconnue : {version!r} (disponibles : {list(data.y_pred)}).")
    settings, members = bootstrap_settings(data, n_resamples, confidence_level, seed)
    y_true, y_pred, scores = data.y_true, data.y_pred[version], data.scores[version]

    def statistic(idx):
        return compute_metrics(data.classes, y_true[idx], y_pred[idx],
                               scores[idx] if scores is not None else None)

    return BootstrapResult(version, settings, run_bootstrap(data, settings, members, statistic))
