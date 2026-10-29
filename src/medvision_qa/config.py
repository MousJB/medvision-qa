"""Reading and strict validation of the TOML evaluation configuration (docs/evaluation_config.md).

Unknown key, unexpected type or out-of-range value → ``ConfigError``. No field is filled
with a guessed value; an empty metadata field means "not provided".
"""

import hashlib
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from medvision_qa.alignment import EMBEDDED, SEPARATE_FILE
from medvision_qa.classes import ClassSpec, ConfigError
from medvision_qa.confidence_intervals import validate_settings
from medvision_qa.i18n import Text, msg
from medvision_qa.metrics import PER_CLASS_METRICS

SCHEMA_VERSION = "0.1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")

CRITERION_KINDS = ("absolute", "non_inferiority", "superiority")
CRITERION_METRICS = ("accuracy", "macro_f1") + PER_CLASS_METRICS + ("sensitivity", "specificity", "auroc")
BINARY_METRICS = ("sensitivity", "specificity", "auroc")

SAMPLE_SIZE_STATUSES = ("provided", "not_provided", "not_applicable", "based_on_data_availability")
DATA_NATURES = ("synthetic", "clinical", "not_provided")


@dataclass(frozen=True)
class VersionConfig:
    name: str  # "A" or "B"
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
    version: str | None  # absolute: evaluated version

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
            raise ConfigError(msg("cfg.section_missing", where=where))
        return {}
    value = parent[key]
    if not isinstance(value, dict):
        raise ConfigError(msg("cfg.not_a_table", where=where))
    return value


def _check_keys(table: dict, where: str, required: tuple, optional: tuple = ()):
    unknown = sorted(set(table) - set(required) - set(optional))
    if unknown:
        raise ConfigError(msg("cfg.unknown_keys", where=where, keys=str(unknown)))
    missing = [k for k in required if k not in table]
    if missing:
        raise ConfigError(msg("cfg.missing_keys", where=where, keys=str(missing)))


def _str(table: dict, key: str, where: str, *, required_non_empty=False, default="") -> str:
    value = table.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(msg("cfg.not_a_string", where=f"{where}.{key}"))
    if value != value.strip():
        raise ConfigError(msg("cfg.value_whitespace", where=f"{where}.{key}"))
    if required_non_empty and value == "":
        raise ConfigError(msg("cfg.empty", where=f"{where}.{key}"))
    return value


def _pattern(value: str, pattern: re.Pattern, where: str, description: Text) -> str:
    if value and not pattern.fullmatch(value):
        raise ConfigError(msg("cfg.pattern", where=where, description=description, value=repr(value)))
    return value


def _number(value, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigError(msg("cfg.not_a_number", where=where))
    return float(value)


def _one_of(value, allowed, where: str):
    if value not in allowed:
        raise ConfigError(msg("cfg.one_of", where=where, values=str(list(allowed))))
    return value


def _data_path(base: Path, value: str, where: str) -> Path:
    """Path relative to the configuration folder, without leaving that folder."""
    if value == "":
        raise ConfigError(msg("cfg.empty", where=where))
    # Absolute under either convention, whatever the OS: the same configuration is rejected
    # for the same reason on Windows and on Linux.
    windows = PureWindowsPath(value)
    if PurePosixPath(value).is_absolute() or windows.drive or windows.root:
        raise ConfigError(msg("cfg.absolute_path", where=where))
    relative = Path(value)
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(base):
        raise ConfigError(msg("cfg.path_escapes", where=where, value=repr(value)))
    if not resolved.is_file():
        raise ConfigError(msg("cfg.file_not_found", where=where, value=repr(value)))
    return resolved


def _classes(raw: dict) -> ClassSpec:
    table = _table(raw, "classes", "classes")
    _check_keys(table, "classes", ("order",), ("positive",))
    order, positive = table["order"], table.get("positive", [])
    if not isinstance(order, list):
        raise ConfigError(msg("cfg.not_a_list", where="classes.order"))
    if not isinstance(positive, list):
        raise ConfigError(msg("cfg.positive_not_list"))
    return ClassSpec(tuple(order), tuple(positive))


def _versions(raw: dict, base: Path) -> dict[str, VersionConfig]:
    table = _table(raw, "versions", "versions")
    unknown = sorted(set(table) - {"A", "B"})
    if unknown:
        raise ConfigError(msg("cfg.unknown_versions", names=str(unknown)))
    if "A" not in table:
        raise ConfigError(msg("cfg.version_a_missing"))
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
                                 msg("cfg.desc_commit")),
            weights_sha256=_pattern(_str(t, "weights_sha256", where), SHA256_PATTERN,
                                    f"{where}.weights_sha256", msg("cfg.desc_sha256")),
            preprocessing=_str(t, "preprocessing", where),
            description=_str(t, "description", where),
        )
    if "B" in versions and versions["A"].id == versions["B"].id:
        raise ConfigError(msg("cfg.same_version_ids"))
    return versions


def _statistics(raw: dict):
    table = _table(raw, "statistics", "statistics")
    _check_keys(table, "statistics", ("confidence_level", "bootstrap_resamples", "seed"),
                ("probability_sum_tolerance",))
    validate_settings(table["bootstrap_resamples"], table["confidence_level"], table["seed"])
    tolerance = _number(table.get("probability_sum_tolerance", 1e-3), "statistics.probability_sum_tolerance")
    if tolerance <= 0:
        raise ConfigError(msg("cfg.tolerance_positive"))
    return float(table["confidence_level"]), table["bootstrap_resamples"], table["seed"], tolerance


def _sample_size(raw: dict) -> SampleSize:
    table = _table(raw, "sample_size", "sample_size")
    _check_keys(table, "sample_size", ("status",), ("justification",))
    status = _one_of(_str(table, "status", "sample_size"), SAMPLE_SIZE_STATUSES, "sample_size.status")
    justification = _str(table, "justification", "sample_size")
    if status in ("provided", "not_applicable") and not justification:
        raise ConfigError(msg("cfg.justification_required", status=repr(status)))
    if status == "not_provided" and justification:
        raise ConfigError(msg("cfg.justification_must_be_empty"))
    return SampleSize(status, justification)


def _criteria(raw: dict, classes: ClassSpec, versions: dict) -> tuple[Criterion, ...]:
    items = raw.get("criteria")
    if not items:
        raise ConfigError(msg("cfg.no_criteria"))
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise ConfigError(msg("cfg.criteria_not_tables"))
    criteria, seen = [], set()
    for n, item in enumerate(items, start=1):
        where = f"criteria[{n}]"
        kind = _one_of(item.get("kind"), CRITERION_KINDS, f"{where}.kind")
        extra = {"absolute": ("threshold", "version"), "non_inferiority": ("margin",), "superiority": ()}[kind]
        required = ("id", "description", "kind", "metric") + (("threshold",) if kind == "absolute" else ()) \
            + (("margin",) if kind == "non_inferiority" else ())
        _check_keys(item, where, required, extra + ("class",))

        cid = _str(item, "id", where, required_non_empty=True)
        if cid in seen:
            raise ConfigError(msg("cfg.duplicate_criterion", id=repr(cid)))
        seen.add(cid)

        metric = _one_of(_str(item, "metric", where), CRITERION_METRICS, f"{where}.metric")
        class_name = item.get("class")
        if metric in PER_CLASS_METRICS:
            if class_name not in classes.order:
                raise ConfigError(msg("cfg.class_required", where=where, metric=repr(metric),
                                      classes=str(list(classes.order))))
        elif class_name is not None:
            raise ConfigError(msg("cfg.class_meaningless", where=where, metric=repr(metric)))
        if metric in BINARY_METRICS and not classes.positive:
            raise ConfigError(msg("cfg.positive_required", where=where, metric=repr(metric)))

        threshold = margin = version = None
        if kind == "absolute":
            threshold = _number(item["threshold"], f"{where}.threshold")
            if not 0 <= threshold <= 1:
                raise ConfigError(msg("cfg.threshold_range", where=where))
            version = item.get("version", "B" if "B" in versions else "A")
            if version not in versions:
                raise ConfigError(msg("cfg.version_undeclared", where=where, version=repr(version)))
        else:
            if "B" not in versions:
                raise ConfigError(msg("cfg.b_required", where=where, kind=repr(kind)))
            if kind == "non_inferiority":
                margin = _number(item["margin"], f"{where}.margin")
                if not 0 < margin < 1:
                    raise ConfigError(msg("cfg.margin_range", where=where))
        criteria.append(Criterion(cid, _str(item, "description", where, required_non_empty=True),
                                  kind, metric, class_name, threshold, margin, version))
    return tuple(criteria)


def load_config(path) -> EvaluationConfig:
    path = Path(path).resolve()
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise ConfigError(msg("cfg.unreadable", name=path.name, error=exc.strerror or str(exc))) from exc
    try:
        raw = tomllib.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(msg("cfg.unreadable", name=path.name, error=str(exc))) from exc
    base = path.parent

    _check_keys(raw, "root", ("schema_version", "evaluation", "classes", "data", "versions",
                              "statistics", "sample_size", "criteria"))
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(msg("cfg.schema_version", found=repr(raw["schema_version"]),
                              expected=repr(SCHEMA_VERSION)))

    evaluation = _table(raw, "evaluation", "evaluation")
    _check_keys(evaluation, "evaluation", ("title",), ("objective",))
    classes = _classes(raw)

    data = _table(raw, "data", "data")
    _check_keys(data, "data", ("ground_truth_mode",), ("ground_truth_file", "description", "nature", "manifest_sha256"))
    mode = _str(data, "ground_truth_mode", "data")
    if mode not in (SEPARATE_FILE, EMBEDDED):
        raise ConfigError(msg("cfg.gt_mode", a=repr(SEPARATE_FILE), b=repr(EMBEDDED)))
    gt_value = _str(data, "ground_truth_file", "data")
    if mode == SEPARATE_FILE:
        ground_truth_file = _data_path(base, gt_value, "data.ground_truth_file")
    elif gt_value:
        raise ConfigError(msg("cfg.gt_file_must_be_empty"))
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
        data_nature=_one_of(_str(data, "nature", "data", default="not_provided"), DATA_NATURES, "data.nature"),
        manifest_sha256=_pattern(_str(data, "manifest_sha256", "data"), SHA256_PATTERN,
                                 "data.manifest_sha256", msg("cfg.desc_sha256")),
        versions=versions,
        confidence_level=confidence_level,
        bootstrap_resamples=resamples,
        seed=seed,
        probability_sum_tolerance=tolerance,
        sample_size=_sample_size(raw),
        criteria=_criteria(raw, classes, versions),
    )
