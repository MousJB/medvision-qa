"""Lecture et validation stricte de la configuration d'évaluation TOML (docs/evaluation_config.md).

Clé inconnue, type inattendu ou valeur hors domaine → ``ConfigError``. Aucun champ n'est
complété par une valeur devinée ; un champ de métadonnées vide signifie « non fourni ».
"""

import hashlib
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from medvision_qa.alignment import EMBEDDED, SEPARATE_FILE
from medvision_qa.classes import ClassSpec, ConfigError
from medvision_qa.confidence_intervals import validate_settings
from medvision_qa.metrics import PER_CLASS_METRICS

SCHEMA_VERSION = "0.1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")

CRITERION_KINDS = ("absolute", "non_inferiority", "superiority")
CRITERION_METRICS = ("accuracy", "macro_f1") + PER_CLASS_METRICS + ("sensitivity", "specificity", "auroc")
BINARY_METRICS = ("sensitivity", "specificity", "auroc")

SAMPLE_SIZE_STATUSES = ("provided", "not_provided", "not_applicable", "based_on_data_availability")
NOT_PROVIDED = "Not provided"
DATA_NATURES = ("synthetic", "clinical", "not_provided")


@dataclass(frozen=True)
class VersionConfig:
    name: str  # "A" ou "B"
    id: str
    predictions_file: Path
    code_commit: str
    weights_sha256: str
    preprocessing: str
    description: str


@dataclass(frozen=True)
class Criterion:
    id: str
    description: str
    kind: str
    metric: str
    class_name: str | None
    threshold: float | None  # absolute
    margin: float | None  # non_inferiority
    version: str | None  # absolute : version évaluée

    @property
    def metric_key(self) -> str:
        return f"{self.metric}[{self.class_name}]" if self.class_name else self.metric


@dataclass(frozen=True)
class SampleSize:
    status: str
    justification: str


@dataclass(frozen=True)
class EvaluationConfig:
    path: Path
    sha256: str
    title: str
    objective: str
    classes: ClassSpec
    ground_truth_mode: str
    ground_truth_file: Path | None
    data_description: str
    data_nature: str
    manifest_sha256: str
    versions: dict[str, VersionConfig]
    confidence_level: float
    bootstrap_resamples: int
    seed: int
    probability_sum_tolerance: float
    sample_size: SampleSize
    criteria: tuple[Criterion, ...]


def _table(parent: dict, key: str, where: str, required=True) -> dict:
    if key not in parent:
        if required:
            raise ConfigError(f"Section [{where}] absente.")
        return {}
    value = parent[key]
    if not isinstance(value, dict):
        raise ConfigError(f"[{where}] doit être une table.")
    return value


def _check_keys(table: dict, where: str, required: tuple, optional: tuple = ()):
    unknown = sorted(set(table) - set(required) - set(optional))
    if unknown:
        raise ConfigError(f"Clé(s) inconnue(s) dans [{where}] : {unknown}.")
    missing = [k for k in required if k not in table]
    if missing:
        raise ConfigError(f"Clé(s) obligatoire(s) absente(s) dans [{where}] : {missing}.")


def _str(table: dict, key: str, where: str, *, required_non_empty=False, default="") -> str:
    value = table.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(f"{where}.{key} doit être une chaîne.")
    if value != value.strip():
        raise ConfigError(f"{where}.{key} : espace en début ou fin de valeur.")
    if required_non_empty and value == "":
        raise ConfigError(f"{where}.{key} ne doit pas être vide.")
    return value


def _pattern(value: str, pattern: re.Pattern, where: str, description: str) -> str:
    if value and not pattern.fullmatch(value):
        raise ConfigError(f"{where} : {description} attendu (ou vide si non fourni), reçu {value!r}.")
    return value


def _number(value, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigError(f"{where} doit être un nombre fini.")
    return float(value)


def _data_path(base: Path, value: str, where: str) -> Path:
    """Chemin relatif au dossier de la configuration, sans sortie de ce dossier."""
    if value == "":
        raise ConfigError(f"{where} ne doit pas être vide.")
    relative = Path(value)
    if relative.is_absolute() or relative.drive:
        raise ConfigError(f"{where} : chemin absolu refusé ; indiquer un chemin relatif au "
                          "dossier de la configuration.")
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base):
        raise ConfigError(f"{where} : le chemin sort du dossier de la configuration ({value!r}).")
    if not resolved.is_file():
        raise ConfigError(f"{where} : fichier introuvable ({value!r}).")
    return resolved


def _data_nature(data: dict) -> str:
    nature = _str(data, "nature", "data", default="not_provided")
    if nature not in DATA_NATURES:
        raise ConfigError(f"data.nature doit valoir l'un de {list(DATA_NATURES)}.")
    return nature


def _classes(raw: dict) -> ClassSpec:
    table = _table(raw, "classes", "classes")
    _check_keys(table, "classes", ("order",), ("positive",))
    order, positive = table["order"], table.get("positive", [])
    if not isinstance(order, list):
        raise ConfigError("classes.order doit être une liste.")
    if not isinstance(positive, list):
        raise ConfigError('classes.positive doit être une liste, par ex. ["glioma"].')
    return ClassSpec(tuple(order), tuple(positive))


def _versions(raw: dict, base: Path) -> dict[str, VersionConfig]:
    table = _table(raw, "versions", "versions")
    unknown = sorted(set(table) - {"A", "B"})
    if unknown:
        raise ConfigError(f"Versions inconnues : {unknown} (seules A et B sont prévues).")
    if "A" not in table:
        raise ConfigError("[versions.A] absente : la version de référence est obligatoire.")
    versions = {}
    for name in ("A", "B"):
        if name not in table:
            continue
        where = f"versions.{name}"
        t = _table(table, name, where)
        _check_keys(t, where, ("id", "predictions_file"), ("code_commit", "weights_sha256", "preprocessing", "description"))
        versions[name] = VersionConfig(
            name=name,
            id=_str(t, "id", where, required_non_empty=True),
            predictions_file=_data_path(base, _str(t, "predictions_file", where), f"{where}.predictions_file"),
            code_commit=_pattern(_str(t, "code_commit", where), COMMIT_PATTERN, f"{where}.code_commit",
                                 "hash de commit hexadécimal (7 à 40 caractères, minuscules)"),
            weights_sha256=_pattern(_str(t, "weights_sha256", where), SHA256_PATTERN,
                                    f"{where}.weights_sha256", "SHA-256 hexadécimal en minuscules"),
            preprocessing=_str(t, "preprocessing", where),
            description=_str(t, "description", where),
        )
    if "B" in versions and versions["A"].id == versions["B"].id:
        raise ConfigError("versions.A.id et versions.B.id doivent être différents.")
    return versions


def _statistics(raw: dict):
    table = _table(raw, "statistics", "statistics")
    _check_keys(table, "statistics", ("confidence_level", "bootstrap_resamples", "seed"),
                ("probability_sum_tolerance",))
    validate_settings(table["bootstrap_resamples"], table["confidence_level"], table["seed"])
    tolerance = _number(table.get("probability_sum_tolerance", 1e-3), "statistics.probability_sum_tolerance")
    if tolerance <= 0:
        raise ConfigError("statistics.probability_sum_tolerance doit être > 0.")
    return float(table["confidence_level"]), table["bootstrap_resamples"], table["seed"], tolerance


def _sample_size(raw: dict) -> SampleSize:
    table = _table(raw, "sample_size", "sample_size")
    _check_keys(table, "sample_size", ("status",), ("justification",))
    status = _str(table, "status", "sample_size")
    if status not in SAMPLE_SIZE_STATUSES:
        raise ConfigError(f"sample_size.status doit valoir l'un de {list(SAMPLE_SIZE_STATUSES)}.")
    justification = _str(table, "justification", "sample_size")
    if status in ("provided", "not_applicable") and not justification:
        raise ConfigError(f"sample_size.justification est obligatoire pour le statut {status!r}.")
    if status == "not_provided" and justification:
        raise ConfigError("sample_size.justification doit être vide pour le statut 'not_provided'.")
    return SampleSize(status, justification)


def _criteria(raw: dict, classes: ClassSpec, versions: dict) -> tuple[Criterion, ...]:
    items = raw.get("criteria")
    if not items:
        raise ConfigError("Aucun critère [[criteria]] : une évaluation sans critère ne produit "
                          "pas de décision.")
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise ConfigError("[[criteria]] doit être une liste de tables.")
    criteria, seen = [], set()
    for n, item in enumerate(items, start=1):
        where = f"criteria[{n}]"
        kind = item.get("kind")
        if kind not in CRITERION_KINDS:
            raise ConfigError(f"{where}.kind doit valoir l'un de {list(CRITERION_KINDS)}.")
        extra = {"absolute": ("threshold", "version"), "non_inferiority": ("margin",), "superiority": ()}[kind]
        required = ("id", "description", "kind", "metric") + (("threshold",) if kind == "absolute" else ()) \
            + (("margin",) if kind == "non_inferiority" else ())
        _check_keys(item, where, required, extra + ("class",))

        cid = _str(item, "id", where, required_non_empty=True)
        if cid in seen:
            raise ConfigError(f"Identifiant de critère dupliqué : {cid!r}.")
        seen.add(cid)

        metric = _str(item, "metric", where)
        if metric not in CRITERION_METRICS:
            raise ConfigError(f"{where}.metric doit valoir l'un de {list(CRITERION_METRICS)}.")
        class_name = item.get("class")
        if metric in PER_CLASS_METRICS:
            if class_name not in classes.order:
                raise ConfigError(f"{where} : la métrique {metric!r} exige `class` parmi {list(classes.order)}.")
        elif class_name is not None:
            raise ConfigError(f"{where} : `class` n'a pas de sens pour la métrique {metric!r}.")
        if metric in BINARY_METRICS and not classes.positive:
            raise ConfigError(f"{where} : la métrique {metric!r} exige classes.positive.")

        threshold = margin = version = None
        if kind == "absolute":
            threshold = _number(item["threshold"], f"{where}.threshold")
            if not 0 <= threshold <= 1:
                raise ConfigError(f"{where}.threshold doit être dans [0, 1].")
            version = item.get("version", "B" if "B" in versions else "A")
            if version not in versions:
                raise ConfigError(f"{where}.version : version {version!r} non déclarée.")
        else:
            if "B" not in versions:
                raise ConfigError(f"{where} : un critère {kind!r} exige [versions.B].")
            if kind == "non_inferiority":
                margin = _number(item["margin"], f"{where}.margin")
                if not 0 < margin < 1:
                    raise ConfigError(f"{where}.margin doit être dans ]0, 1[.")
        criteria.append(Criterion(cid, _str(item, "description", where, required_non_empty=True),
                                  kind, metric, class_name, threshold, margin, version))
    return tuple(criteria)


def load_config(path) -> EvaluationConfig:
    path = Path(path).resolve()
    raw_bytes = path.read_bytes()
    try:
        raw = tomllib.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"Configuration illisible ({path.name}) : {exc}") from exc
    base = path.parent

    _check_keys(raw, "racine", ("schema_version", "evaluation", "classes", "data", "versions",
                                "statistics", "sample_size", "criteria"))
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(f"schema_version {raw['schema_version']!r} non pris en charge "
                          f"(attendu : {SCHEMA_VERSION!r}).")

    evaluation = _table(raw, "evaluation", "evaluation")
    _check_keys(evaluation, "evaluation", ("title",), ("objective",))
    classes = _classes(raw)

    data = _table(raw, "data", "data")
    _check_keys(data, "data", ("ground_truth_mode",), ("ground_truth_file", "description", "nature", "manifest_sha256"))
    mode = _str(data, "ground_truth_mode", "data")
    if mode not in (SEPARATE_FILE, EMBEDDED):
        raise ConfigError(f"data.ground_truth_mode doit valoir {SEPARATE_FILE!r} ou {EMBEDDED!r}.")
    gt_value = _str(data, "ground_truth_file", "data")
    if mode == SEPARATE_FILE:
        ground_truth_file = _data_path(base, gt_value, "data.ground_truth_file")
    elif gt_value:
        raise ConfigError("data.ground_truth_file doit être vide en mode 'embedded'.")
    else:
        ground_truth_file = None

    versions = _versions(raw, base)
    confidence_level, resamples, seed, tolerance = _statistics(raw)

    return EvaluationConfig(
        path=path,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        title=_str(evaluation, "title", "evaluation", required_non_empty=True),
        objective=_str(evaluation, "objective", "evaluation"),
        classes=classes,
        ground_truth_mode=mode,
        ground_truth_file=ground_truth_file,
        data_description=_str(data, "description", "data"),
        data_nature=_data_nature(data),
        manifest_sha256=_pattern(_str(data, "manifest_sha256", "data"), SHA256_PATTERN,
                                 "data.manifest_sha256", "SHA-256 hexadécimal en minuscules"),
        versions=versions,
        confidence_level=confidence_level,
        bootstrap_resamples=resamples,
        seed=seed,
        probability_sum_tolerance=tolerance,
        sample_size=_sample_size(raw),
        criteria=_criteria(raw, classes, versions),
    )
