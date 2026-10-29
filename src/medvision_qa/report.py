"""Version Verification Record : rapport HTML autonome (docs/report.md).

Le rapport n'affiche que ce que contient ``EvaluationResult``. Toute information absente
est affichée « Not provided » ou listée comme non disponible, jamais complétée.
"""

from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from medvision_qa.config import NOT_PROVIDED
from medvision_qa.decision_engine import AGGREGATION_RULE
from medvision_qa.evaluation import EvaluationResult
from medvision_qa.metrics import DEFINITIONS

SAMPLE_SIZE_LABELS = {
    "provided": "Provided",
    "not_provided": "Not provided",
    "not_applicable": "Not applicable",
    "based_on_data_availability": "Based on data availability",
}
DATA_NATURE_LABELS = {
    "synthetic": "Données synthétiques",
    "clinical": "Données cliniques réelles (déclaré par l'utilisateur)",
    "not_provided": NOT_PROVIDED,
}
DATA_AVAILABILITY_WARNING = ("Une taille d'échantillon dictée par la disponibilité des données ne "
                             "constitue pas une justification statistique.")

CANNOT_ESTABLISH = (
    "Un résultat non significatif ne prouve pas l'absence de régression, l'équivalence ou la "
    "non-infériorité.",
    "Cette analyse n'est pas une validation clinique ni une démonstration de sécurité clinique.",
    "Ce rapport ne certifie pas la conformité à ISO 13485, au FDA QMSR ou à une autre réglementation.",
    "Des tests de sensibilité synthétiques ne valident pas les conditions réelles d'acquisition "
    "clinique.",
    "La détection de quasi-doublons ne prouve pas à elle seule une fuite de données ni l'identité "
    "d'un patient.",
    "Les conclusions sont limitées aux données, au protocole, aux hypothèses et aux méthodes "
    "effectivement utilisés.",
)

_env = Environment(loader=PackageLoader("medvision_qa", "templates"),
                   autoescape=select_autoescape(default=True, default_for_string=True),
                   undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


def _num(x) -> str:
    return "—" if x is None else f"{x:.4f}"


def _p_value(p) -> str:
    return "—" if p is None else ("< 0.0001" if p < 1e-4 else f"{p:.4f}")


def _or_not_provided(value: str) -> str:
    return value if value else NOT_PROVIDED


def _interval_cell(ci) -> dict:
    note = ci.undefined_reason if not ci.defined else "; ".join(ci.warnings)
    return {"estimate": _num(ci.estimate.value), "lower": _num(ci.lower), "upper": _num(ci.upper),
            "note": note, "defined": ci.defined}


def _not_available(result: EvaluationResult) -> list[str]:
    cfg = result.config
    items = []
    if not cfg.objective:
        items.append("Objectif de l'évaluation (evaluation.objective) : Not provided")
    if not cfg.data_description:
        items.append("Description des données (data.description) : Not provided")
    if cfg.data_nature == "not_provided":
        items.append("Nature des données (data.nature) : Not provided")
    if not cfg.manifest_sha256:
        items.append("Hash SHA-256 du manifeste de données (data.manifest_sha256) : Not provided")
    for v in cfg.versions.values():
        for field, label in (("code_commit", "commit du code"), ("weights_sha256", "hash des poids"),
                             ("preprocessing", "prétraitement"), ("description", "description")):
            if not getattr(v, field):
                items.append(f"Version {v.name} — {label} (versions.{v.name}.{field}) : Not provided")
    if cfg.sample_size.status == "not_provided":
        items.append("Justification de la taille d'échantillon : Not provided")
    if result.data.groups is None:
        items.append("Identifiants patient (patient_id) : non fournis ; pas de rééchantillonnage par patient")
    for name, res in result.per_version.items():
        for key, ci in res.intervals.items():
            if not ci.estimate.defined:
                items.append(f"Version {name} — {key} : indéfinie ({ci.estimate.undefined_reason})")
            elif not ci.defined:
                items.append(f"Version {name} — IC de {key} : non calculable ({ci.undefined_reason})")
    if result.mcnemar is not None and result.mcnemar.p_value is None:
        items.append(f"Test de McNemar : non applicable ({result.mcnemar.not_applicable_reason})")
    if result.differences is not None:
        items.append(f"Test de DeLong : {result.delong_status}")
    else:
        items.append("Comparaison entre versions : non exécutée (une seule version déclarée)")
    items.append("Tests de robustesse : non exécutés (non pris en charge par cette version de l'outil)")
    return items


def _limitations(result: EvaluationResult) -> list[str]:
    cfg = result.config
    items = []
    if cfg.data_nature == "synthetic":
        items.append("Les données sont synthétiques : ces résultats ne renseignent pas sur les "
                     "performances sur des données réelles.")
    elif cfg.data_nature == "not_provided":
        items.append("La nature des données (synthétiques ou réelles) n'est pas déclarée.")
    if result.data.groups is None:
        items.append("Sans identifiant patient, les cas sont supposés indépendants. Si plusieurs "
                     "images proviennent du même patient, les intervalles de confiance sont trop "
                     "étroits.")
    items.append("Bootstrap percentile : la couverture réelle peut être inférieure au niveau nominal "
                 "pour les petits échantillons et les métriques proches de 0 ou 1.")
    if any(w for res in result.per_version.values() for ci in res.intervals.values() for w in ci.warnings):
        items.append("Certains intervalles portent des avertissements (voir section 11).")
    if len(cfg.criteria) > 1:
        items.append(f"{len(cfg.criteria)} critères évalués sans correction de multiplicité.")
    items.append("L'outil ne peut pas prouver que les critères ont été définis avant l'analyse ; le "
                 "hash de la configuration permet de le vérifier contre un historique externe (git).")
    items.append("L'alignement vérifie la cohérence des identifiants de cas, pas que ces identifiants "
                 "désignent les mêmes images pour toutes les versions.")
    items.append("Les métriques portent sur la décision multiclasse (argmax) ; aucun seuil de décision "
                 "alternatif n'est évalué.")
    return items


def build_context(result: EvaluationResult) -> dict:
    cfg, data = result.config, result.data
    base = cfg.path.parent

    def rel(path: Path) -> str:
        return path.relative_to(base).as_posix()

    files = []
    if result.ground_truth is not None:
        files.append(("Vérité terrain", rel(cfg.ground_truth_file), result.ground_truth.source))
    for name, v in cfg.versions.items():
        files.append((f"Prédictions version {name}", rel(v.predictions_file), result.predictions[name].source))

    versions = [{
        "name": v.name, "id": v.id, "description": _or_not_provided(v.description),
        "code_commit": _or_not_provided(v.code_commit),
        "weights_sha256": _or_not_provided(v.weights_sha256),
        "preprocessing": _or_not_provided(v.preprocessing),
        "has_scores": data.scores[v.name] is not None,
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
        "result": result,
        "title": cfg.title,
        "objective": _or_not_provided(cfg.objective),
        "run": result.run,
        "decision": result.decision,
        "aggregation_rule": AGGREGATION_RULE,
        "data_nature": cfg.data_nature,
        "data_nature_label": DATA_NATURE_LABELS[cfg.data_nature],
        "data_description": _or_not_provided(cfg.data_description),
        "manifest_sha256": _or_not_provided(cfg.manifest_sha256),
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
                      "cell": _interval_cell(r.interval),
                      "parameter": (f"seuil {_num(r.criterion.threshold)}" if r.criterion.kind == "absolute"
                                    else f"marge {_num(r.criterion.margin)}" if r.criterion.kind == "non_inferiority"
                                    else "Δ > 0")}
                     for r in result.decision.criteria],
        "sample_size_label": SAMPLE_SIZE_LABELS[status],
        "sample_size_text": cfg.sample_size.justification,
        "sample_size_warning": DATA_AVAILABILITY_WARNING if status == "based_on_data_availability" else None,
        "not_available": _not_available(result),
        "limitations": _limitations(result),
        "cannot_establish": CANNOT_ESTABLISH,
        "not_provided": NOT_PROVIDED,
    }


def render_report(result: EvaluationResult) -> str:
    return _env.get_template("report.html.j2").render(**build_context(result))


def write_report(result: EvaluationResult, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(result), encoding="utf-8")
    return path
