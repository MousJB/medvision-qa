"""Lecture et validation stricte des CSV d'entrée (docs/data_format.md).

Toute violation est collectée puis levée sous forme de ``ValidationError``. Aucune ligne
n'est supprimée et aucune valeur n'est corrigée, normalisée ou remplacée.
"""

import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass
from pathlib import Path

from medvision_qa.classes import ClassSpec

META_PREFIX = "meta_"
SCORE_PREFIX = "score_"
# Nombre décimal simple : refuse ce que float() accepte en plus ("nan", "inf", "1_000").
DECIMAL_PATTERN = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
MAX_ISSUES_IN_MESSAGE = 20


@dataclass(frozen=True)
class ValidationIssue:
    """Une violation. ``line`` : ligne physique du fichier (1 = en-tête)."""

    file: str
    rule: str
    message: str
    line: int | None = None
    column: str | None = None
    value: str | None = None

    def __str__(self):
        where = self.file
        if self.line is not None:
            where += f", ligne {self.line}"
        if self.column is not None:
            where += f", colonne {self.column!r}"
        value = f" (valeur : {self.value!r})" if self.value is not None else ""
        return f"[{self.rule}] {where} : {self.message}{value}"


class ValidationError(Exception):
    """Données invalides. ``issues`` contient la liste complète des violations."""

    def __init__(self, issues):
        self.issues = tuple(issues)
        shown = "\n".join(f"  - {issue}" for issue in self.issues[:MAX_ISSUES_IN_MESSAGE])
        hidden = len(self.issues) - MAX_ISSUES_IN_MESSAGE
        more = f"\n  ... et {hidden} autre(s) problème(s)" if hidden > 0 else ""
        super().__init__(f"{len(self.issues)} problème(s) de validation :\n{shown}{more}")


@dataclass(frozen=True)
class SourceInfo:
    path: str
    sha256: str
    n_rows: int
    checks: tuple[str, ...]


@dataclass(frozen=True)
class GroundTruth:
    source: SourceInfo
    labels: dict[str, str]
    patient_ids: dict[str, str] | None


@dataclass(frozen=True)
class Predictions:
    source: SourceInfo
    predicted: dict[str, str]
    scores: dict[str, tuple[float, ...]] | None  # dans l'ordre de ClassSpec.order
    true_labels: dict[str, str] | None


COMMON_CHECKS = (
    "encoding_utf8", "csv_syntax", "header_present", "no_duplicate_columns",
    "no_unknown_columns", "required_columns", "field_count", "no_empty_lines",
    "no_surrounding_whitespace", "required_values_present", "unique_case_id",
    "labels_declared",
)


def _read_rows(path: Path, issues: list[ValidationIssue]):
    """Retourne (sha256, en-tête, [(numéro de ligne, champs)]) ou None si illisible."""
    name = str(path)
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        issues.append(ValidationIssue(name, "encoding_utf8",
                                      f"le fichier n'est pas en UTF-8 (octet {exc.start})"))
        return None

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows = []
    try:
        for fields in reader:
            rows.append((reader.line_num, fields))
    except csv.Error as exc:
        issues.append(ValidationIssue(name, "csv_syntax", f"CSV mal formé : {exc}",
                                      line=reader.line_num))
        return None

    if not rows or rows[0][1] == []:
        issues.append(ValidationIssue(name, "header_present", "en-tête absent", line=1))
        return None
    header = rows[0][1]
    return sha256, header, rows[1:]


def _check_header(name, header, required, optional, issues):
    for col in header:
        if col != col.strip():
            issues.append(ValidationIssue(name, "no_surrounding_whitespace",
                                          "espace en début ou fin de nom de colonne",
                                          line=1, value=col))
    duplicates = sorted({c for c in header if header.count(c) > 1})
    for col in duplicates:
        issues.append(ValidationIssue(name, "no_duplicate_columns", "colonne dupliquée",
                                      line=1, column=col))
    for col in required:
        if col not in header:
            issues.append(ValidationIssue(name, "required_columns", "colonne obligatoire absente",
                                          line=1, column=col))
    allowed = set(required) | set(optional)
    for col in header:
        if col not in allowed and not col.startswith(META_PREFIX) and not col.startswith(SCORE_PREFIX):
            issues.append(ValidationIssue(
                name, "no_unknown_columns",
                f"colonne inconnue ; préfixer par {META_PREFIX!r} pour la conserver sans l'utiliser",
                line=1, column=col))


def _parse_records(name, header, rows, required_values, issues):
    """Vérifie la structure ligne par ligne ; retourne [(ligne, {colonne: valeur})]."""
    records = []
    if not rows:
        issues.append(ValidationIssue(name, "no_data_rows", "aucune ligne de données"))
    for line, fields in rows:
        if fields == []:
            issues.append(ValidationIssue(name, "no_empty_lines", "ligne vide", line=line))
            continue
        if len(fields) != len(header):
            issues.append(ValidationIssue(
                name, "field_count",
                f"{len(fields)} champ(s) au lieu de {len(header)}", line=line))
            continue
        record = dict(zip(header, fields))
        for col, value in record.items():
            if value != value.strip():
                issues.append(ValidationIssue(name, "no_surrounding_whitespace",
                                              "espace en début ou fin de valeur",
                                              line=line, column=col, value=value))
        for col in required_values:
            if col in record and record[col] == "":
                issues.append(ValidationIssue(name, "required_values_present", "valeur manquante",
                                              line=line, column=col))
        records.append((line, record))
    return records


def _check_unique_ids(name, records, issues):
    first_seen = {}
    for line, record in records:
        case_id = record.get("case_id", "")
        if case_id == "":
            continue
        if case_id in first_seen:
            issues.append(ValidationIssue(
                name, "unique_case_id", f"case_id déjà présent ligne {first_seen[case_id]}",
                line=line, column="case_id", value=case_id))
        else:
            first_seen[case_id] = line


def _check_label(name, line, column, value, classes, issues):
    if value != "" and value not in classes.order:
        issues.append(ValidationIssue(
            name, "labels_declared",
            f"label non déclaré (classes : {list(classes.order)} ; sensible à la casse)",
            line=line, column=column, value=value))


def load_ground_truth(path, classes: ClassSpec) -> GroundTruth:
    path = Path(path)
    name = str(path)
    issues: list[ValidationIssue] = []
    parsed = _read_rows(path, issues)
    if parsed is None:
        raise ValidationError(issues)
    sha256, header, rows = parsed

    required = ("case_id", "true_label")
    _check_header(name, header, required, ("patient_id",), issues)
    for col in header:
        if col.startswith(SCORE_PREFIX):
            issues.append(ValidationIssue(name, "no_unknown_columns",
                                          "colonne de score inattendue dans la vérité terrain",
                                          line=1, column=col))
    has_patient = "patient_id" in header
    required_values = required + (("patient_id",) if has_patient else ())
    records = _parse_records(name, header, rows, required_values, issues)
    _check_unique_ids(name, records, issues)
    for line, record in records:
        _check_label(name, line, "true_label", record.get("true_label", ""), classes, issues)

    if issues:
        raise ValidationError(issues)

    checks = COMMON_CHECKS + (("patient_id_present",) if has_patient else ())
    return GroundTruth(
        source=SourceInfo(name, sha256, len(records), checks),
        labels={r["case_id"]: r["true_label"] for _, r in records},
        patient_ids={r["case_id"]: r["patient_id"] for _, r in records} if has_patient else None,
    )


def _parse_score(name, line, column, value, issues):
    if not DECIMAL_PATTERN.fullmatch(value):
        issues.append(ValidationIssue(name, "score_numeric",
                                      "score non numérique (format décimal attendu)",
                                      line=line, column=column, value=value))
        return None
    score = float(value)
    if not math.isfinite(score):
        issues.append(ValidationIssue(name, "score_finite", "score non fini",
                                      line=line, column=column, value=value))
        return None
    if not 0.0 <= score <= 1.0:
        issues.append(ValidationIssue(name, "score_in_bounds", "score hors de [0, 1]",
                                      line=line, column=column, value=value))
        return None
    return score


def load_predictions(path, classes: ClassSpec, probability_sum_tolerance: float = 1e-3) -> Predictions:
    if not (isinstance(probability_sum_tolerance, (int, float))
            and math.isfinite(probability_sum_tolerance) and probability_sum_tolerance > 0):
        raise ValueError("probability_sum_tolerance doit être un réel fini > 0.")
    path = Path(path)
    name = str(path)
    issues: list[ValidationIssue] = []
    parsed = _read_rows(path, issues)
    if parsed is None:
        raise ValidationError(issues)
    sha256, header, rows = parsed

    required = ("case_id", "predicted_label")
    _check_header(name, header, required, ("true_label",) + classes.score_columns, issues)

    present_scores = [c for c in header if c.startswith(SCORE_PREFIX)]
    has_scores = bool(present_scores)
    if has_scores:
        for col in present_scores:
            if col not in classes.score_columns:
                issues.append(ValidationIssue(name, "score_columns_complete",
                                              "colonne de score pour une classe non déclarée",
                                              line=1, column=col))
        for col in classes.score_columns:
            if col not in header:
                issues.append(ValidationIssue(
                    name, "score_columns_complete",
                    "colonne de score manquante (les scores sont « tout ou rien »)",
                    line=1, column=col))
    if issues:  # en-tête invalide : la lecture ligne à ligne n'aurait pas de sens
        raise ValidationError(issues)

    has_true = "true_label" in header
    required_values = (required + (classes.score_columns if has_scores else ())
                       + (("true_label",) if has_true else ()))
    records = _parse_records(name, header, rows, required_values, issues)
    _check_unique_ids(name, records, issues)

    scores = {}
    for line, record in records:
        predicted = record["predicted_label"]
        _check_label(name, line, "predicted_label", predicted, classes, issues)
        if has_true:
            _check_label(name, line, "true_label", record["true_label"], classes, issues)
        if not has_scores:
            continue
        row = [_parse_score(name, line, col, record[col], issues) if record[col] != "" else None
               for col in classes.score_columns]
        if any(s is None for s in row):
            continue
        total = math.fsum(row)
        if abs(total - 1.0) > probability_sum_tolerance:
            issues.append(ValidationIssue(
                name, "score_sum_to_one",
                f"somme des scores = {total!r}, écart à 1 > tolérance {probability_sum_tolerance}",
                line=line))
            continue
        if predicted in classes.order:
            best = max(row)
            argmax = [c for c, s in zip(classes.order, row) if s == best]
            if predicted not in argmax:
                issues.append(ValidationIssue(
                    name, "predicted_is_argmax",
                    f"predicted_label n'est pas la classe de score maximal ({argmax})",
                    line=line, column="predicted_label", value=predicted))
        scores[record["case_id"]] = tuple(row)

    if issues:
        raise ValidationError(issues)

    checks = COMMON_CHECKS
    if has_scores:
        checks += ("score_columns_complete", "score_numeric", "score_finite", "score_in_bounds",
                   f"score_sum_to_one(tol={probability_sum_tolerance})", "predicted_is_argmax")
    return Predictions(
        source=SourceInfo(name, sha256, len(records), checks),
        predicted={r["case_id"]: r["predicted_label"] for _, r in records},
        scores=scores if has_scores else None,
        true_labels={r["case_id"]: r["true_label"] for _, r in records} if has_true else None,
    )
