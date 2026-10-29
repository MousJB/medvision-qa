"""Reading and strict validation of the input CSV files (docs/data_format.md).

Every violation is collected, then raised as a ``ValidationError``. No row is removed
and no value is corrected, normalised or replaced.
"""

import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass
from pathlib import Path

from medvision_qa.classes import ClassSpec
from medvision_qa.i18n import DEFAULT_LANGUAGE, Text, msg, t

META_PREFIX = "meta_"
SCORE_PREFIX = "score_"
# Plain decimal number: rejects what float() accepts on top of it ("nan", "inf", "1_000").
DECIMAL_PATTERN = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
MAX_ISSUES_IN_MESSAGE = 20


@dataclass(frozen=True)
class ValidationIssue:
    """One violation. ``line``: physical line of the file (1 = header)."""

    file: str
    rule: str
    message: Text
    line: int | None = None
    column: str | None = None
    value: str | None = None

    def render(self, lang: str = DEFAULT_LANGUAGE) -> str:
        where = self.file
        if self.line is not None:
            where += ", " + t("issue.line", lang, line=self.line)
        if self.column is not None:
            where += ", " + t("issue.column", lang, column=repr(self.column))
        value = t("issue.value", lang, value=repr(self.value)) if self.value is not None else ""
        return f"[{self.rule}] {where}: {self.message.render(lang)}{value}"

    def __str__(self):
        return self.render()


class ValidationError(Exception):
    """Invalid data. ``issues`` holds the complete list of violations."""

    def __init__(self, issues):
        self.issues = tuple(issues)
        shown = "\n".join(f"  - {issue}" for issue in self.issues[:MAX_ISSUES_IN_MESSAGE])
        hidden = len(self.issues) - MAX_ISSUES_IN_MESSAGE
        more = f"\n  ... and {hidden} more issue(s)" if hidden > 0 else ""
        super().__init__(f"{len(self.issues)} validation issue(s):\n{shown}{more}")


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
    scores: dict[str, tuple[float, ...]] | None  # in ClassSpec.order
    true_labels: dict[str, str] | None


COMMON_CHECKS = (
    "encoding_utf8", "csv_syntax", "header_present", "no_duplicate_columns",
    "no_unknown_columns", "required_columns", "field_count", "no_empty_lines",
    "no_surrounding_whitespace", "required_values_present", "unique_case_id",
    "labels_declared",
)


def _read_rows(path: Path, issues: list[ValidationIssue]):
    """Returns (sha256, header, [(line number, fields)]), or None if unreadable."""
    name = str(path)
    raw = path.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        issues.append(ValidationIssue(name, "encoding_utf8", msg("val.not_utf8", offset=exc.start)))
        return None

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows = []
    try:
        for fields in reader:
            rows.append((reader.line_num, fields))
    except csv.Error as exc:
        issues.append(ValidationIssue(name, "csv_syntax", msg("val.csv_malformed", error=str(exc)),
                                      line=reader.line_num))
        return None

    if not rows or rows[0][1] == []:
        issues.append(ValidationIssue(name, "header_present", msg("val.header_missing"), line=1))
        return None
    header = rows[0][1]
    return sha256, header, rows[1:]


def _check_header(name, header, required, optional, issues):
    for col in header:
        if col != col.strip():
            issues.append(ValidationIssue(name, "no_surrounding_whitespace", msg("val.column_whitespace"),
                                          line=1, value=col))
    duplicates = sorted({c for c in header if header.count(c) > 1})
    for col in duplicates:
        issues.append(ValidationIssue(name, "no_duplicate_columns", msg("val.duplicate_column"),
                                      line=1, column=col))
    for col in required:
        if col not in header:
            issues.append(ValidationIssue(name, "required_columns", msg("val.required_column_missing"),
                                          line=1, column=col))
    allowed = set(required) | set(optional)
    for col in header:
        if col not in allowed and not col.startswith(META_PREFIX) and not col.startswith(SCORE_PREFIX):
            issues.append(ValidationIssue(name, "no_unknown_columns",
                                          msg("val.unknown_column", prefix=repr(META_PREFIX)),
                                          line=1, column=col))


def _parse_records(name, header, rows, required_values, issues):
    """Checks the structure row by row; returns [(line, {column: value})]."""
    records = []
    if not rows:
        issues.append(ValidationIssue(name, "no_data_rows", msg("val.no_data_rows")))
    for line, fields in rows:
        if fields == []:
            issues.append(ValidationIssue(name, "no_empty_lines", msg("val.empty_line"), line=line))
            continue
        if len(fields) != len(header):
            issues.append(ValidationIssue(
                name, "field_count", msg("val.field_count", found=len(fields), expected=len(header)),
                line=line))
            continue
        record = dict(zip(header, fields))
        for col, value in record.items():
            if value != value.strip():
                issues.append(ValidationIssue(name, "no_surrounding_whitespace", msg("val.value_whitespace"),
                                              line=line, column=col, value=value))
        for col in required_values:
            if col in record and record[col] == "":
                issues.append(ValidationIssue(name, "required_values_present", msg("val.value_missing"),
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
                name, "unique_case_id", msg("val.duplicate_case_id", line=first_seen[case_id]),
                line=line, column="case_id", value=case_id))
        else:
            first_seen[case_id] = line


def _check_label(name, line, column, value, classes, issues):
    if value != "" and value not in classes.order:
        issues.append(ValidationIssue(
            name, "labels_declared", msg("val.label_undeclared", classes=str(list(classes.order))),
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
            issues.append(ValidationIssue(name, "no_unknown_columns", msg("val.unexpected_score_column"),
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
        issues.append(ValidationIssue(name, "score_numeric", msg("val.score_not_numeric"),
                                      line=line, column=column, value=value))
        return None
    score = float(value)
    if not math.isfinite(score):
        issues.append(ValidationIssue(name, "score_finite", msg("val.score_not_finite"),
                                      line=line, column=column, value=value))
        return None
    if not 0.0 <= score <= 1.0:
        issues.append(ValidationIssue(name, "score_in_bounds", msg("val.score_out_of_bounds"),
                                      line=line, column=column, value=value))
        return None
    return score


def load_predictions(path, classes: ClassSpec, probability_sum_tolerance: float = 1e-3) -> Predictions:
    if not (isinstance(probability_sum_tolerance, (int, float))
            and math.isfinite(probability_sum_tolerance) and probability_sum_tolerance > 0):
        raise ValueError("probability_sum_tolerance must be a finite number > 0.")
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
                issues.append(ValidationIssue(name, "score_columns_complete", msg("val.score_column_undeclared"),
                                              line=1, column=col))
        for col in classes.score_columns:
            if col not in header:
                issues.append(ValidationIssue(name, "score_columns_complete", msg("val.score_column_missing"),
                                              line=1, column=col))
    if issues:  # invalid header: reading row by row would make no sense
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
                msg("val.score_sum", total=repr(total), tolerance=probability_sum_tolerance), line=line))
            continue
        if predicted in classes.order:
            best = max(row)
            argmax = [c for c, s in zip(classes.order, row) if s == best]
            if predicted not in argmax:
                issues.append(ValidationIssue(
                    name, "predicted_is_argmax", msg("val.not_argmax", argmax=str(argmax)),
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
