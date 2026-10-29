"""HTML report: mandatory sections, nothing invented, self-contained, reproducible, both languages."""

import importlib.util
import re
from pathlib import Path

import numpy as np
import pytest
from markupsafe import escape

from medvision_qa.__main__ import main
from medvision_qa.evaluation import run_evaluation
from medvision_qa.report import CANNOT_ESTABLISH, DATA_AVAILABILITY_WARNING, render_report

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "synthetic_demo"
CLASSES = ("glioma", "meningioma", "notumor", "pituitary")

CRITERION = ('[[criteria]]\nid = "C1"\ndescription = "NI accuracy"\nkind = "non_inferiority"\n'
             'metric = "accuracy"\nmargin = 0.05\n')
ABSOLUTE = ('[[criteria]]\nid = "C1"\ndescription = "threshold"\nkind = "absolute"\n'
            'metric = "accuracy"\nthreshold = 0.5\n')


def predictions_csv(rng, case_ids, y, accuracy):
    lines = ["case_id,predicted_label," + ",".join(f"score_{c}" for c in CLASSES)]
    for case_id, t in zip(case_ids, y):
        target = t if rng.random() < accuracy else (t + 1) % 4
        p = np.full(4, 0.1)
        p[target] = 0.7
        lines.append(f"{case_id},{CLASSES[target]}," + ",".join(f"{v:.1f}" for v in p))
    return "\n".join(lines) + "\n"


@pytest.fixture
def make_eval(tmp_path):
    def _make(*, title="Test", data_extra="", versions_extra="", sample_size='status = "not_provided"',
              criteria=CRITERION, with_b=True, n=120):
        rng = np.random.default_rng(0)
        case_ids = [f"c{i:03d}" for i in range(n)]
        y = rng.integers(0, 4, n)
        (tmp_path / "gt.csv").write_text("case_id,true_label\n" + "".join(
            f"{c},{CLASSES[t]}\n" for c, t in zip(case_ids, y)), encoding="utf-8")
        (tmp_path / "a.csv").write_text(predictions_csv(rng, case_ids, y, 0.8), encoding="utf-8")
        (tmp_path / "b.csv").write_text(predictions_csv(rng, case_ids, y, 0.85), encoding="utf-8")
        b = f'[versions.B]\nid = "v2"\npredictions_file = "b.csv"\n{versions_extra}' if with_b else ""
        config = tmp_path / "config.toml"
        config.write_text(f'''schema_version = "0.1"
[evaluation]
title = {title!r}
[classes]
order = {list(CLASSES)!r}
positive = ["glioma", "meningioma", "pituitary"]
[data]
ground_truth_mode = "separate_file"
ground_truth_file = "gt.csv"
{data_extra}
[versions.A]
id = "v1"
predictions_file = "a.csv"
{versions_extra}
{b}
[statistics]
confidence_level = 0.95
bootstrap_resamples = 1000
seed = 3
[sample_size]
{sample_size}
{criteria}''', encoding="utf-8")
        return config
    return _make


@pytest.fixture
def html(make_eval):
    return render_report(run_evaluation(make_eval()))


def test_all_21_sections_present_in_order(html):
    numbers = [int(n) for n in re.findall(r'<h2 id="s(\d+)">', html)]
    assert numbers == list(range(1, 22))
    assert '<h2 id="s21">21. What This Report Cannot Establish</h2>' in html


def test_cannot_establish_minimum_text(html):
    section = html[html.index('id="s21"'):]
    for sentence in CANNOT_ESTABLISH:
        assert str(escape(str(sentence))) in section


def test_standalone_no_external_resources(html):
    assert "<script" not in html.lower()
    assert not re.search(r'(src|href)\s*=\s*"(?!#)', html)  # internal anchor links only
    assert "http://" not in html and "https://" not in html
    assert "@import" not in html


def test_missing_metadata_shown_as_not_provided(html):
    for field in ("versions.A.code_commit", "versions.B.weights_sha256", "data.manifest_sha256",
                  "evaluation.objective", "data.nature"):
        assert f"({field}): Not provided" in html
    assert re.search(r"Justification</dt><dd><span class=\"not-provided\">Not provided</span>", html)


def test_missing_metadata_not_provided_in_each_section(html):
    def section(n):
        return html[html.index(f'id="s{n}"'):html.index(f'id="s{n + 1}"')]

    marker = '<span class="not-provided">Not provided</span>'
    assert section(5).count(marker) == 4  # commit + weights, versions A and B
    assert section(6).count(marker) == 3  # description, nature, manifest hash
    assert section(8).count(marker) == 2  # preprocessing A and B
    assert section(3).count(marker) == 1  # objective
    assert section(4).count(marker) == 2  # version descriptions


def test_provided_metadata_rendered_verbatim(make_eval):
    sha = "ab" * 32
    config = make_eval(versions_extra=f'code_commit = "1a2b3c4d"\nweights_sha256 = "{sha}"\n'
                                      'preprocessing = "z-score"\n',
                       data_extra=f'description = "test set"\nnature = "clinical"\nmanifest_sha256 = "{sha}"')
    out = render_report(run_evaluation(config))
    assert "1a2b3c4d" in out and sha in out and "z-score" in out and "test set" in out
    assert "code_commit): Not provided" not in out
    assert "Synthetic data." not in out


def test_synthetic_banner(make_eval):
    out = render_report(run_evaluation(make_eval(data_extra='nature = "synthetic"')))
    assert "<strong>Synthetic data.</strong>" in out


def test_numbers_match_computed_results(make_eval):
    result = run_evaluation(make_eval())
    out = render_report(result)
    for r in result.decision.criteria:
        assert f"[{r.interval.lower:.4f}, {r.interval.upper:.4f}]" in out
        assert str(escape(str(r.reason))) in out
    a = result.per_version["A"].intervals["macro_f1"]
    assert f"{a.estimate.value:.4f}" in out
    for row in result.confusion_matrices["A"]:
        assert "".join(f'<td class="num">{n}</td>' for n in row) in out
    for source in (result.ground_truth.source, result.predictions["B"].source):
        assert source.sha256 in out
    assert result.config.sha256 in out


def test_user_text_is_escaped(make_eval):
    out = render_report(run_evaluation(make_eval(title="<script>alert(1)</script>")))
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out


def test_no_absolute_paths_in_report(make_eval, tmp_path):
    out = render_report(run_evaluation(make_eval()))
    assert str(tmp_path) not in out and tmp_path.as_posix() not in out
    assert "<code>gt.csv</code>" in out


@pytest.mark.parametrize("sample_size, label, text, warning", [
    ('status = "provided"\njustification = "Power 80%, delta 0.05, McNemar"',
     "Provided", "Power 80%, delta 0.05, McNemar", False),
    ('status = "not_provided"', "Not provided", None, False),
    ('status = "not_applicable"\njustification = "pilot study"', "Not applicable", "pilot study", False),
    ('status = "based_on_data_availability"', "Based on data availability", None, True),
])
def test_sample_size_states(make_eval, sample_size, label, text, warning):
    out = render_report(run_evaluation(make_eval(sample_size=sample_size)))
    section = out[out.index('id="s17"'):out.index('id="s18"')]
    assert label in section
    assert "Actual size</dt><dd>120 cases" in section
    assert (text in section) if text else ("Text provided" not in section)
    assert (str(DATA_AVAILABILITY_WARNING) in section) == warning


def test_single_version_report(make_eval):
    out = render_report(run_evaluation(make_eval(with_b=False, criteria=ABSOLUTE)))
    assert "Evaluation of a single version" in out
    assert "Comparison between versions: not run" in out


def test_rendering_is_deterministic(make_eval):
    config = make_eval()
    result = run_evaluation(config)
    assert render_report(result) == render_report(result)

    other = run_evaluation(config)

    def normalise(text, r):
        return text.replace(r.run.run_id, "RUN").replace(r.run.started_at_utc, "TIME")

    assert normalise(render_report(result), result) == normalise(render_report(other), other)


def test_cli_writes_report(make_eval, tmp_path, capsys):
    out = tmp_path / "report.html"
    assert main([str(make_eval()), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert "Report:" in capsys.readouterr().out


def test_cli_invalid_data_produces_no_report(make_eval, tmp_path, capsys):
    config = make_eval()
    (tmp_path / "b.csv").write_text("case_id,predicted_label\nc000,glioma\n", encoding="utf-8")
    out = tmp_path / "report.html"
    assert main([str(config), "-o", str(out)]) == 2
    assert not out.exists()
    assert "no report produced" in capsys.readouterr().err


def test_demo_data_regenerates_identically(tmp_path):
    spec = importlib.util.spec_from_file_location("demo_generate", DEMO / "generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(tmp_path)
    for name in ("ground_truth.csv", "preds_v1.csv", "preds_v2.csv"):
        assert (tmp_path / name).read_bytes() == (DEMO / name).read_bytes(), name


def test_demo_config_runs():
    result = run_evaluation(DEMO / "config.toml")
    assert result.config.data_nature == "synthetic"
    assert result.per_version["A"].settings.unit == "patient"
    assert "<h2 id=\"s21\">" in render_report(result)


# --- Japanese report ---------------------------------------------------------------------

JAPANESE = re.compile(r"[぀-ヿ一-鿿]")


def test_japanese_report_has_same_structure_and_numbers(make_eval):
    result = run_evaluation(make_eval(data_extra='nature = "synthetic"'))
    en, ja = render_report(result, "en"), render_report(result, "ja")
    assert '<html lang="ja">' in ja and '<html lang="en">' in en
    assert [int(n) for n in re.findall(r'<h2 id="s(\d+)">', ja)] == list(range(1, 22))
    assert "What This Report Cannot Establish（本レポートで立証できないこと）" in ja
    assert "<strong>合成データ。</strong>" in ja
    for r in result.decision.criteria:
        assert f"[{r.interval.lower:.4f}, {r.interval.upper:.4f}]" in ja
        assert str(escape(r.reason.render("ja"))) in ja
    assert re.findall(r'<td class="num">[^<]*</td>', en) == re.findall(r'<td class="num">[^<]*</td>', ja)
    assert result.config.sha256 in ja


def test_japanese_report_text_is_translated(make_eval):
    ja = render_report(run_evaluation(make_eval()), "ja")
    section = ja[ja.index('id="s19"'):ja.index('id="s20"')]
    assert "（versions.A.code_commit）: 未提供" in section
    for item in re.findall(r"<li>(.*?)</li>", ja[ja.index('id="s19"'):]):
        assert JAPANESE.search(item), item
    for sentence in CANNOT_ESTABLISH:
        assert sentence.render("ja") in ja


def test_unknown_language_rejected(make_eval):
    with pytest.raises(ValueError):
        render_report(run_evaluation(make_eval()), "fr")


def test_cli_language_option(make_eval, tmp_path):
    out = tmp_path / "report.ja.html"
    assert main([str(make_eval()), "-o", str(out), "--lang", "ja"]) == 0
    assert '<html lang="ja">' in out.read_text(encoding="utf-8")
