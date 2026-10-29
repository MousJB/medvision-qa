"""Percentile bootstrap confidence intervals (docs/metrics.md § 3).

Resampling unit: the patient when ``patient_id`` is provided (cluster bootstrap),
otherwise the case. An interval is produced only if the metric is defined on the full
sample and in every resample.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from medvision_qa.alignment import AlignedData
from medvision_qa.classes import ConfigError
from medvision_qa.i18n import Text, msg
from medvision_qa.metrics import MetricValue, compute_metrics

MIN_RESAMPLES = 1000
SMALL_SAMPLE_UNITS = 30
METHOD = "percentile"
QUANTILE_METHOD = "linear"
ZERO_WIDTH_WARNING = msg("ci.zero_width_warning")


@dataclass(frozen=True)
class BootstrapSettings:
    n_resamples: int
    confidence_level: float
    seed: int
    unit: str  # "case" or "patient"
    n_units: int
    method: str = METHOD
    quantile_method: str = QUANTILE_METHOD


@dataclass(frozen=True)
class ConfidenceInterval:
    estimate: MetricValue
    lower: float | None
    upper: float | None
    undefined_reason: Text | None
    warnings: tuple[Text, ...]

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
        raise ConfigError(msg("cfg.resamples_invalid", min=MIN_RESAMPLES))
    if (isinstance(confidence_level, bool) or not isinstance(confidence_level, (int, float))
            or not math.isfinite(confidence_level) or not 0 < confidence_level < 1):
        raise ConfigError(msg("cfg.confidence_level_invalid"))
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ConfigError(msg("cfg.seed_invalid"))


def group_members(groups: np.ndarray) -> list[np.ndarray]:
    """Case indices of each patient."""
    order = np.argsort(groups, kind="stable")
    boundaries = np.flatnonzero(np.diff(groups[order])) + 1
    return np.split(order, boundaries)


def resample_indices(rng: np.random.Generator, n_cases: int,
                     members: list[np.ndarray] | None) -> np.ndarray:
    """Draws units with replacement; with ``members``, returns every case of the drawn patients."""
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
    """Applies ``statistic`` (case indices → metrics) to the full sample, then to every
    resample, and builds one percentile interval per key."""
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
                                  msg("ci.metric_undefined", reason=estimate.undefined_reason), ())
    if undefined_count:
        return ConfidenceInterval(
            estimate, None, None,
            msg("ci.undefined_in_resamples", count=undefined_count, total=settings.n_resamples), ())
    alpha = 1 - settings.confidence_level
    lower, upper = np.quantile(samples, [alpha / 2, 1 - alpha / 2], method=QUANTILE_METHOD)
    warnings = []
    if lower == upper:
        warnings.append(ZERO_WIDTH_WARNING)
    if settings.n_units < SMALL_SAMPLE_UNITS:
        warnings.append(msg("ci.small_sample", n=settings.n_units, min=SMALL_SAMPLE_UNITS))
    return ConfidenceInterval(estimate, float(lower), float(upper), None, tuple(warnings))


def bootstrap_metrics(data: AlignedData, version: str, *, n_resamples: int,
                      confidence_level: float, seed: int) -> BootstrapResult:
    """Confidence intervals of every metric of one version."""
    if version not in data.y_pred:
        raise KeyError(f"Unknown version: {version!r} (available: {list(data.y_pred)}).")
    settings, members = bootstrap_settings(data, n_resamples, confidence_level, seed)
    y_true, y_pred, scores = data.y_true, data.y_pred[version], data.scores[version]

    def statistic(idx):
        return compute_metrics(data.classes, y_true[idx], y_pred[idx],
                               scores[idx] if scores is not None else None)

    return BootstrapResult(version, settings, run_bootstrap(data, settings, members, statistic))
