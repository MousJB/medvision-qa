"""Version Verification Record: self-contained HTML report (docs/report.md).

The report only shows what ``EvaluationResult`` contains. Any missing information is shown
as "Not provided" or listed as not available, never filled in. The report can be rendered
in English or Japanese (``lang``); both renderings carry the same content.
"""

from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from medvision_qa.decision_engine import AGGREGATION_RULE
from medvision_qa.evaluation import EvaluationResult
from medvision_qa.i18n import DEFAULT_LANGUAGE, Text, check_language, msg, t
from medvision_qa.metrics import DEFINITIONS

DATA_AVAILABILITY_WARNING = msg("r.availability_warning")
CANNOT_ESTABLISH = tuple(msg(f"cannot.{i}") for i in range(1, 7))

_env = Environment(loader=PackageLoader("medvision_qa", "templates"),
                   autoescape=select_autoescape(default=True, default_for_string=True),
                   undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


def _num(x) -> str:
    return "—" if x is None else f"{x:.4f}"


def _p_value(p) -> str:
    return "—" if p is None else ("< 0.0001" if p < 1e-4 else f"{p:.4f}")


def _or_none(value: str) -> str | None:
    """Empty metadata → None, shown as "Not provided" in the report's language."""
    return value or None


def _interval_cell(ci) -> dict:
    notes = (ci.undefined_reason,) if not ci.defined else ci.warnings
    return {"estimate": _num(ci.estimate.value), "lower": _num(ci.lower), "upper": _num(ci.upper),
            "notes": notes, "defined": ci.defined}


def not_available(result: EvaluationResult) -> list[Text]:
    cfg = result.config
    items = []
    if not cfg.objective:
        items.append(msg("na.objective"))
    if not cfg.data_description:
        items.append(msg("na.data_description"))
    if cfg.data_nature == "not_provided":
        items.append(msg("na.data_nature"))
    if not cfg.manifest_sha256:
        items.append(msg("na.manifest"))
    for v in cfg.versions.values():
        for field in ("code_commit", "weights_sha256", "preprocessing", "description"):
            if not getattr(v, field):
                items.append(msg("na.version_field", v=v.name, label=msg(f"field.{field}"), field=field))
    if cfg.sample_size.status == "not_provided":
        items.append(msg("na.sample_size"))
    if result.data.groups is None:
        items.append(msg("na.patient_ids"))
    for name, res in result.per_version.items():
        for key, ci in res.intervals.items():
            if not ci.estimate.defined:
                items.append(msg("na.metric_undefined", v=name, key=key, reason=ci.estimate.undefined_reason))
            elif not ci.defined:
                items.append(msg("na.ci_undefined", v=name, key=key, reason=ci.undefined_reason))
    if result.mcnemar is not None and result.mcnemar.p_value is None:
        items.append(msg("na.mcnemar", reason=result.mcnemar.not_applicable_reason))
    if result.differences is not None:
        items.append(msg("na.delong", status=result.delong_status))
    else:
        items.append(msg("na.no_comparison"))
    items.append(msg("na.robustness"))
    return items


def limitations(result: EvaluationResult) -> list[Text]:
    cfg = result.config
    items = []
    if cfg.data_nature == "synthetic":
        items.append(msg("lim.synthetic"))
    elif cfg.data_nature == "not_provided":
        items.append(msg("lim.nature_unknown"))
    if result.data.groups is None:
        items.append(msg("lim.no_patient_id"))
    items.append(msg("lim.percentile"))
    if any(w for res in result.per_version.values() for ci in res.intervals.values() for w in ci.warnings):
        items.append(msg("lim.warnings"))
    if len(cfg.criteria) > 1:
        items.append(msg("lim.multiplicity", n=len(cfg.criteria)))
    items.append(msg("lim.preregistration"))
    items.append(msg("lim.alignment"))
    items.append(msg("lim.argmax"))
    return items


def _parameter(criterion) -> Text | str:
    if criterion.kind == "absolute":
        return msg("r.threshold", t=_num(criterion.threshold))
    if criterion.kind == "non_inferiority":
        return msg("r.margin", m=_num(criterion.margin))
    return "Δ > 0"


def build_context(result: EvaluationResult, lang: str = DEFAULT_LANGUAGE) -> dict:
    lang = check_language(lang)
    cfg, data = result.config, result.data
    base = cfg.path.parent

    def rel(path: Path) -> str:
        return path.relative_to(base).as_posix()

    def tr(value) -> str:
        return value.render(lang) if isinstance(value, Text) else value

    files = []
    if result.ground_truth is not None:
        files.append((msg("r.ground_truth"), rel(cfg.ground_truth_file), result.ground_truth.source))
    for name, v in cfg.versions.items():
        files.append((msg("r.predictions_of", v=name), rel(v.predictions_file), result.predictions[name].source))

    versions = [{
        "name": v.name, "id": v.id, "description": _or_none(v.description),
        "code_commit": _or_none(v.code_commit), "weights_sha256": _or_none(v.weights_sha256),
        "preprocessing": _or_none(v.preprocessing), "has_scores": data.scores[v.name] is not None,
    } for v in cfg.versions.values()]

    version_names = list(cfg.versions)
    keys = list(result.per_version["A"].intervals)
    metric_rows = [{"key": k,
                    "cells": [_interval_cell(result.per_version[v].intervals[k]) for v in version_names]}
                   for k in keys]
    difference_rows = ([{"key": k, "cell": _interval_cell(ci)} for k, ci in result.differences.intervals.items()]
                       if result.differences is not None else [])

    status = cfg.sample_size.status
    negatives = [c for c in cfg.classes.order if c not in cfg.classes.positive]
    settings = result.per_version["A"].settings

    return {
        "lang": lang,
        "_": lambda key, **params: t(key, lang, **params),
        "tr": tr,
        "result": result,
        "title": cfg.title,
        "objective": _or_none(cfg.objective),
        "run": result.run,
        "decision": result.decision,
        "aggregation_rule": AGGREGATION_RULE,
        "data_nature": cfg.data_nature,
        "data_nature_label": (msg(f"r.nature.{cfg.data_nature}") if cfg.data_nature != "not_provided" else None),
        "data_description": _or_none(cfg.data_description),
        "manifest_sha256": _or_none(cfg.manifest_sha256),
        "config_file": cfg.path.name,
        "config_sha256": cfg.sha256,
        "versions": versions,
        "version_names": version_names,
        "files": files,
        "classes": cfg.classes.order,
        "positive": cfg.classes.positive,
        "negatives": negatives,
        "ground_truth_mode": data.ground_truth_mode,
        "n_cases": data.n_cases,
        "settings": settings,
        "statistics": {"confidence_level": cfg.confidence_level, "resamples": cfg.bootstrap_resamples,
                       "seed": cfg.seed, "tolerance": cfg.probability_sum_tolerance},
        "definitions": DEFINITIONS,
        "metric_rows": metric_rows,
        "confusion": [(v, result.confusion_matrices[v]) for v in version_names],
        "difference_rows": difference_rows,
        "mcnemar": result.mcnemar,
        "mcnemar_p": _p_value(result.mcnemar.p_value) if result.mcnemar else None,
        "delong_status": result.delong_status,
        "criteria": [{"c": r.criterion, "state": r.state, "reason": r.reason, "quantity": r.quantity,
                      "cell": _interval_cell(r.interval), "parameter": _parameter(r.criterion)}
                     for r in result.decision.criteria],
        "sample_size_label": None if status == "not_provided" else msg(f"r.sample.{status}"),
        "sample_size_text": cfg.sample_size.justification,
        "sample_size_warning": DATA_AVAILABILITY_WARNING if status == "based_on_data_availability" else None,
        "not_available": not_available(result),
        "limitations": limitations(result),
        "cannot_establish": CANNOT_ESTABLISH,
    }


def render_report(result: EvaluationResult, lang: str = DEFAULT_LANGUAGE) -> str:
    return _env.get_template("report.html.j2").render(**build_context(result, lang))


def write_report(result: EvaluationResult, path, lang: str = DEFAULT_LANGUAGE) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(result, lang), encoding="utf-8", newline="\n")  # same bytes on every OS
    return path
