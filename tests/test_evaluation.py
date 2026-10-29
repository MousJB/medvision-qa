"""Intégration : configuration TOML + CSV synthétiques → décision."""

import numpy as np
import pytest

from medvision_qa.decision_engine import INCONCLUSIVE, NOT_SATISFIED, SATISFIED
from medvision_qa.evaluation import run_evaluation
from medvision_qa.validation import ValidationError

CLASSES = ("glioma", "meningioma", "notumor", "pituitary")


def write_predictions(path, case_ids, y_true, accuracy, rng):
    n, k = len(case_ids), len(CLASSES)
    logits = rng.normal(0, 1, (n, k))
    correct = rng.random(n) < accuracy
    target = np.where(correct, y_true, (y_true + rng.integers(1, k, n)) % k)
    logits[np.arange(n), target] += 6
    p = np.exp(logits)
    p /= p.sum(axis=1, keepdims=True)
    lines = ["case_id,predicted_label," + ",".join(f"score_{c}" for c in CLASSES)]
    for i in rng.permutation(n):
        scores = [f"{v:.8f}" for v in p[i]]
        best = CLASSES[int(np.argmax([float(s) for s in scores]))]
        lines.append(f"{case_ids[i]},{best}," + ",".join(scores))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def scenario(tmp_path):
    def _scenario(acc_a, acc_b, criteria, n=600, seed=0):
        rng = np.random.default_rng(seed)
        case_ids = [f"img_{i:05d}" for i in range(n)]
        y_true = rng.integers(0, len(CLASSES), n)
        (tmp_path / "gt.csv").write_text(
            "case_id,true_label\n" + "".join(f"{c},{CLASSES[y]}\n" for c, y in zip(case_ids, y_true)),
            encoding="utf-8")
        write_predictions(tmp_path / "a.csv", case_ids, y_true, acc_a, rng)
        write_predictions(tmp_path / "b.csv", case_ids, y_true, acc_b, rng)
        config = tmp_path / "config.toml"
        config.write_text(f'''schema_version = "0.1"
[evaluation]
title = "Scénario synthétique"
[classes]
order = {list(CLASSES)!r}
positive = ["glioma", "meningioma", "pituitary"]
[data]
ground_truth_mode = "separate_file"
ground_truth_file = "gt.csv"
[versions.A]
id = "v1"
predictions_file = "a.csv"
[versions.B]
id = "v2"
predictions_file = "b.csv"
[statistics]
confidence_level = 0.95
bootstrap_resamples = 1000
seed = 20261029
[sample_size]
status = "based_on_data_availability"
{criteria}''', encoding="utf-8")
        return config
    return _scenario


NI = '[[criteria]]\nid = "NI"\ndescription = "NI accuracy"\nkind = "non_inferiority"\nmetric = "accuracy"\nmargin = 0.03\n'
SUP = '[[criteria]]\nid = "SUP"\ndescription = "Sup AUROC"\nkind = "superiority"\nmetric = "auroc"\n'
ABS = '[[criteria]]\nid = "ABS"\ndescription = "Sensibilité"\nkind = "absolute"\nmetric = "sensitivity"\nthreshold = 0.8\n'


def test_clear_improvement_satisfies_all(scenario):
    result = run_evaluation(scenario(0.80, 0.95, NI + ABS))
    assert result.decision.state == SATISFIED, result.decision.reason
    d = result.differences.intervals["accuracy"]
    assert d.estimate.value > 0.1
    assert result.mcnemar.p_value < 1e-6


def test_clear_regression_not_satisfied(scenario):
    result = run_evaluation(scenario(0.95, 0.80, NI))
    assert result.decision.state == NOT_SATISFIED


def test_close_versions_small_sample_inconclusive(scenario):
    result = run_evaluation(scenario(0.90, 0.89, NI, n=150))
    (criterion,) = result.decision.criteria
    assert criterion.state == INCONCLUSIVE, criterion.reason


def test_run_metadata_recorded(scenario):
    result = run_evaluation(scenario(0.85, 0.85, NI + SUP))
    assert len(result.run.run_id) == 36
    assert result.run.started_at_utc.endswith("+00:00")
    assert set(result.run.packages) == {"medvision-qa", "numpy", "scipy", "scikit-learn", "jinja2"}
    assert result.config.sample_size.status == "based_on_data_availability"
    assert "non implémenté" in result.delong_status
    assert result.predictions["A"].source.sha256 != result.predictions["B"].source.sha256
    assert np.array(result.confusion_matrices["A"]).sum() == 600


def test_reproducible(scenario):
    config = scenario(0.85, 0.87, NI + SUP + ABS)
    a, b = run_evaluation(config), run_evaluation(config)
    assert [(c.state, c.interval) for c in a.decision.criteria] == \
        [(c.state, c.interval) for c in b.decision.criteria]
    assert a.run.run_id != b.run.run_id


def test_invalid_data_blocks_evaluation(scenario, tmp_path):
    config = scenario(0.85, 0.85, NI)
    lines = (tmp_path / "b.csv").read_text(encoding="utf-8").splitlines()
    (tmp_path / "b.csv").write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")  # un cas manquant
    with pytest.raises(ValidationError) as exc:
        run_evaluation(config)
    assert exc.value.issues[0].rule == "same_cases"
