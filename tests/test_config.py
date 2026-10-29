import re
from pathlib import Path

import pytest

from medvision_qa.classes import ConfigError
from medvision_qa.config import load_config

ROOT = Path(__file__).resolve().parents[1]

BASE = '''schema_version = "0.1"

[evaluation]
title = "Test"

[classes]
order = ["glioma", "meningioma", "notumor", "pituitary"]
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
seed = 1

[sample_size]
status = "not_provided"

[[criteria]]
id = "C1"
description = "NI macro-F1"
kind = "non_inferiority"
metric = "macro_f1"
margin = 0.02
'''


@pytest.fixture
def make_config(tmp_path):
    for name in ("gt.csv", "a.csv", "b.csv"):
        (tmp_path / name).write_text("placeholder\n", encoding="utf-8")

    def _make(text=BASE, replace=None):
        if replace:
            for old, new in replace.items():
                assert old in text, old
                text = text.replace(old, new)
        path = tmp_path / "config.toml"
        path.write_text(text, encoding="utf-8")
        return path

    return _make


def test_valid_config(make_config, tmp_path):
    cfg = load_config(make_config())
    assert cfg.classes.positive == ("glioma", "meningioma", "pituitary")
    assert cfg.ground_truth_file == (tmp_path / "gt.csv").resolve()
    assert cfg.versions["B"].code_commit == ""  # not provided, not guessed
    assert cfg.probability_sum_tolerance == 1e-3
    assert re.fullmatch(r"[0-9a-f]{64}", cfg.sha256)
    (criterion,) = cfg.criteria
    assert criterion.metric_key == "macro_f1" and criterion.margin == 0.02


@pytest.mark.parametrize("doc_path", ["docs/evaluation_config.md", "docs/ja/evaluation_config.md"])
def test_documented_example_is_valid(tmp_path, doc_path):
    # The complete example of the configuration guide (both languages) must stay loadable.
    doc = (ROOT / doc_path).read_text(encoding="utf-8")
    example = re.search(r"```toml\n(.*?)```", doc, re.S).group(1)
    for name in ("ground_truth.csv", "preds_v1.csv", "preds_v2.csv"):
        (tmp_path / name).write_text("x\n", encoding="utf-8")
    path = tmp_path / "config.toml"
    path.write_text(example, encoding="utf-8")
    cfg = load_config(path)
    assert [c.id for c in cfg.criteria] == ["C1", "C2"]
    assert cfg.criteria[1].version == "B"


@pytest.mark.parametrize("replace, message", [
    ({'title = "Test"': 'title = "Test"\ntitel = "x"'}, "Unknown key"),
    ({'seed = 1': 'seed = 1\nseeed = 2'}, "Unknown key"),
    ({'seed = 1\n': ''}, "Required key"),
    ({'bootstrap_resamples = 1000': 'bootstrap_resamples = 100'}, "1000"),
    ({'schema_version = "0.1"': 'schema_version = "9"'}, "schema_version"),
    ({'positive = ["glioma", "meningioma", "pituitary"]': 'positive = "glioma"'}, "list"),
    ({'ground_truth_file = "gt.csv"': 'ground_truth_file = "missing.csv"'}, "file not found"),
    ({'ground_truth_file = "gt.csv"': 'ground_truth_file = "../gt.csv"'}, "leaves the configuration folder"),
    ({'ground_truth_file = "gt.csv"': 'ground_truth_file = "C:/gt.csv"'}, "absolute path"),
    ({'ground_truth_mode = "separate_file"': 'ground_truth_mode = "embedded"'}, "must be empty in 'embedded' mode"),
    ({'id = "v2"': 'id = "v1"'}, "must differ"),
    ({'id = "v1"\n': 'id = "v1"\ncode_commit = "main"\n'}, "commit"),
    ({'id = "v1"\n': 'id = "v1"\nweights_sha256 = "abc"\n'}, "SHA-256"),
    ({'status = "not_provided"': 'status = "provided"'}, "is required for status"),
    ({'status = "not_provided"': 'status = "not_provided"\njustification = "x"'}, "must be empty for status"),
    ({'status = "not_provided"': 'status = "maybe"'}, "status"),
    ({'margin = 0.02': 'margin = 0'}, "margin"),
    ({'margin = 0.02': 'margin = -0.02'}, "margin"),
    ({'kind = "non_inferiority"': 'kind = "equivalence"'}, "kind"),
    ({'metric = "macro_f1"': 'metric = "recall"'}, "class"),
    ({'metric = "macro_f1"': 'metric = "dice"'}, "metric"),
])
def test_invalid_configs_rejected(make_config, replace, message):
    with pytest.raises(ConfigError, match=message):
        load_config(make_config(replace=replace))


def test_no_criteria_rejected(make_config):
    text = "criteria = []\n" + BASE[:BASE.index("[[criteria]]")]  # root key: before the tables
    with pytest.raises(ConfigError, match="without criteria"):
        load_config(make_config(text))


def test_duplicate_criterion_id_rejected(make_config):
    text = BASE + BASE[BASE.index("[[criteria]]"):]
    with pytest.raises(ConfigError, match="Duplicate criterion id"):
        load_config(make_config(text))


def test_comparison_criterion_requires_version_b(make_config):
    text = BASE.replace('[versions.B]\nid = "v2"\npredictions_file = "b.csv"\n', "")
    with pytest.raises(ConfigError, match="versions.B"):
        load_config(make_config(text))


def test_absolute_defaults_to_b_and_accepts_explicit_version(make_config):
    absolute = ('\n[[criteria]]\nid = "C2"\ndescription = "threshold"\nkind = "absolute"\n'
                'metric = "recall"\nclass = "glioma"\nthreshold = 0.9\n')
    cfg = load_config(make_config(BASE + absolute))
    assert cfg.criteria[1].version == "B" and cfg.criteria[1].metric_key == "recall[glioma]"
    cfg = load_config(make_config(BASE + absolute + 'version = "A"\n'))
    assert cfg.criteria[1].version == "A"


def test_binary_metric_requires_positive_classes(make_config):
    text = BASE.replace('positive = ["glioma", "meningioma", "pituitary"]\n', "").replace(
        'metric = "macro_f1"', 'metric = "auroc"')
    with pytest.raises(ConfigError, match="positive"):
        load_config(make_config(text))


def test_invalid_toml_rejected(make_config):
    with pytest.raises(ConfigError, match="Unreadable configuration"):
        load_config(make_config("schema_version = \n"))
