import numpy as np
import pytest

from medvision_qa.alignment import AlignedData
from medvision_qa.classes import ClassSpec, ConfigError
from medvision_qa.confidence_intervals import (bootstrap_metrics, group_members,
                                               resample_indices)

SPEC = ClassSpec(("neg", "pos"), ("pos",))


def make_data(y_true, y_pred, scores=None, groups=None, spec=SPEC):
    y_true = np.asarray(y_true)
    return AlignedData(
        classes=spec, ground_truth_mode="separate_file",
        case_ids=tuple(f"c{i:04d}" for i in range(len(y_true))),
        y_true=y_true, y_pred={"A": np.asarray(y_pred)},
        scores={"A": None if scores is None else np.asarray(scores)},
        groups=None if groups is None else np.asarray(groups))


@pytest.fixture
def synthetic():
    rng = np.random.default_rng(0)
    n = 400
    y_true = rng.integers(0, 2, n)
    y_pred = np.where(rng.random(n) < 0.8, y_true, 1 - y_true)
    p_pos = np.clip(0.5 + 0.3 * (2 * y_true - 1) + rng.normal(0, 0.2, n), 0, 1)
    return make_data(y_true, y_pred, np.column_stack([1 - p_pos, p_pos]))


def run(data, **kw):
    params = dict(n_resamples=1000, confidence_level=0.95, seed=1)
    params.update(kw)
    return bootstrap_metrics(data, "A", **params)


def test_reproducible_with_same_seed(synthetic):
    a, b = run(synthetic), run(synthetic)
    assert a.intervals == b.intervals


def test_different_seed_changes_bounds(synthetic):
    a, b = run(synthetic, seed=1), run(synthetic, seed=2)
    assert a.intervals["accuracy"].lower != b.intervals["accuracy"].lower


def test_settings_recorded(synthetic):
    result = run(synthetic)
    s = result.settings
    assert (s.n_resamples, s.confidence_level, s.seed, s.unit, s.n_units, s.method) == (
        1000, 0.95, 1, "case", 400, "percentile")


def test_interval_brackets_estimate(synthetic):
    for key, ci in run(synthetic).intervals.items():
        assert ci.defined, key
        assert ci.lower <= ci.estimate.value <= ci.upper, key


def test_accuracy_close_to_normal_approximation(synthetic):
    # Independent check: for n = 400, the percentile bootstrap must be close to Wald.
    ci = run(synthetic, n_resamples=4000).intervals["accuracy"]
    p, n = ci.estimate.value, synthetic.n_cases
    half_width = 1.959964 * np.sqrt(p * (1 - p) / n)
    assert ci.lower == pytest.approx(p - half_width, abs=0.01)
    assert ci.upper == pytest.approx(p + half_width, abs=0.01)


def test_higher_confidence_gives_wider_interval(synthetic):
    narrow = run(synthetic, confidence_level=0.8).intervals["accuracy"]
    wide = run(synthetic, confidence_level=0.99).intervals["accuracy"]
    assert wide.lower < narrow.lower and wide.upper > narrow.upper


def test_undefined_estimate_gives_no_interval():
    data = make_data([0] * 40, [0] * 40)  # no positive case
    ci = run(data).intervals["sensitivity"]
    assert not ci.defined and str(ci.undefined_reason).startswith("metric undefined")


def test_metric_undefined_in_some_resamples_gives_no_interval():
    # A single positive case: absent from ~37% of the resamples.
    data = make_data([1] + [0] * 39, [1] + [0] * 39)
    ci = run(data).intervals["sensitivity"]
    assert ci.estimate.value == 1.0
    assert not ci.defined
    assert ci.undefined_reason.key == "ci.undefined_in_resamples"


def test_degenerate_interval_warned():
    data = make_data([0, 1] * 20, [0, 1] * 20)
    ci = run(data).intervals["accuracy"]
    assert ci.lower == ci.upper == 1.0
    assert any(w.key == "ci.zero_width_warning" for w in ci.warnings)


def test_small_sample_warned():
    data = make_data([0, 1, 0, 1, 0, 1, 1, 0, 0, 1], [0, 1, 1, 1, 0, 1, 0, 0, 0, 1])
    ci = run(data).intervals["accuracy"]
    assert any("< 30" in str(w) for w in ci.warnings)


def test_patient_level_resampling_keeps_patients_whole():
    groups = np.array([0, 0, 0, 1, 2, 2, 3])
    members = group_members(groups)
    rng = np.random.default_rng(0)
    for _ in range(200):
        idx = resample_indices(rng, len(groups), members)
        drawn = groups[idx]
        for g in np.unique(drawn):
            # each drawn patient appears with all of its cases, a whole number of times
            assert np.sum(drawn == g) % np.sum(groups == g) == 0


def test_patient_unit_recorded_and_wider_with_correlated_cases():
    # 20 patients × 10 images, identical predictions within a patient: the real
    # uncertainty is that of 20 units, not 200.
    rng = np.random.default_rng(3)
    correct_by_patient = rng.random(20) < 0.7
    groups = np.repeat(np.arange(20), 10)
    y_true = np.zeros(200, dtype=int)
    y_pred = np.where(correct_by_patient[groups], 0, 1)
    case = run(make_data(y_true, y_pred)).intervals["accuracy"]
    clustered_result = run(make_data(y_true, y_pred, groups=groups))
    clustered = clustered_result.intervals["accuracy"]
    assert clustered_result.settings.unit == "patient"
    assert clustered_result.settings.n_units == 20
    assert (clustered.upper - clustered.lower) > 2 * (case.upper - case.lower)


@pytest.mark.parametrize("kw", [
    {"n_resamples": 999},
    {"n_resamples": 1000.0},
    {"confidence_level": 1.0},
    {"confidence_level": 0},
    {"confidence_level": float("nan")},
    {"seed": None},
    {"seed": -1},
    {"seed": True},
])
def test_invalid_settings_rejected(synthetic, kw):
    with pytest.raises(ConfigError):
        run(synthetic, **kw)


def test_unknown_version_rejected(synthetic):
    with pytest.raises(KeyError):
        bootstrap_metrics(synthetic, "B", n_resamples=1000, confidence_level=0.95, seed=1)
