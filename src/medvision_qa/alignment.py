"""Explicit case alignment on ``case_id`` (docs/data_format.md § 5-6).

The sets of ``case_id`` must be identical: no matching by position, no implicit
intersection.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from medvision_qa.classes import ClassSpec
from medvision_qa.i18n import msg
from medvision_qa.validation import GroundTruth, Predictions, ValidationError, ValidationIssue

SEPARATE_FILE = "separate_file"
EMBEDDED = "embedded"


@dataclass(frozen=True)
class AlignedData:
    """Aligned data, sorted by ``case_id`` so that file order does not matter.

    ``y_true`` / ``y_pred``: indices into ``classes.order``. ``scores[v]``: (n, k)
    matrix or None. ``groups``: patient index per case, or None.
    """

    classes: ClassSpec
    ground_truth_mode: str
    case_ids: tuple[str, ...]
    y_true: np.ndarray
    y_pred: dict[str, np.ndarray]
    scores: dict[str, np.ndarray | None]
    groups: np.ndarray | None

    @property
    def n_cases(self) -> int:
        return len(self.case_ids)


def _compare_ids(reference_name, reference_ids, other_name, other_ids, issues):
    for case_id in sorted(reference_ids - other_ids):
        issues.append(ValidationIssue(other_name, "same_cases",
                                      msg("val.case_missing_here", reference=reference_name),
                                      column="case_id", value=case_id))
    for case_id in sorted(other_ids - reference_ids):
        issues.append(ValidationIssue(other_name, "same_cases",
                                      msg("val.case_extra", reference=reference_name),
                                      column="case_id", value=case_id))


def _compare_labels(reference_name, reference, other_name, other, issues):
    for case_id in sorted(reference.keys() & other.keys()):
        if reference[case_id] != other[case_id]:
            issues.append(ValidationIssue(
                other_name, "true_label_consistent",
                msg("val.true_label_mismatch", reference=reference_name, expected=repr(reference[case_id])),
                column="true_label", value=f"{case_id}: {other[case_id]}"))


def align(classes: ClassSpec, predictions: Mapping[str, Predictions],
          ground_truth: GroundTruth | None = None) -> AlignedData:
    """Aligns one or more versions (``{"A": ..., "B": ...}``) on the ground truth.

    ``ground_truth`` given: ``separate_file`` mode. Absent: ``embedded`` mode, and every
    predictions file must then contain ``true_label``.
    """
    if not predictions:
        raise ValueError("At least one predictions version is required.")
    issues: list[ValidationIssue] = []
    versions = list(predictions)

    if ground_truth is not None:
        mode = SEPARATE_FILE
        reference_name = ground_truth.source.path
        labels = ground_truth.labels
    else:
        mode = EMBEDDED
        missing = [v for v in versions if predictions[v].true_labels is None]
        if missing:
            raise ValidationError([
                ValidationIssue(predictions[v].source.path, "true_label_available",
                                msg("val.true_label_required"), column="true_label")
                for v in missing])
        reference_name = predictions[versions[0]].source.path
        labels = predictions[versions[0]].true_labels

    reference_ids = set(labels)
    for v in versions:
        pred = predictions[v]
        _compare_ids(reference_name, reference_ids, pred.source.path, set(pred.predicted), issues)
        is_reference = mode == EMBEDDED and v == versions[0]
        if pred.true_labels is not None and not is_reference:
            _compare_labels(reference_name, labels, pred.source.path, pred.true_labels, issues)
    if issues:
        raise ValidationError(issues)

    case_ids = tuple(sorted(reference_ids))
    index = classes.index
    y_true = np.array([index[labels[c]] for c in case_ids], dtype=np.int64)
    y_pred = {v: np.array([index[predictions[v].predicted[c]] for c in case_ids], dtype=np.int64)
              for v in versions}
    scores = {v: (np.array([predictions[v].scores[c] for c in case_ids], dtype=np.float64)
                  if predictions[v].scores is not None else None)
              for v in versions}

    groups = None
    if ground_truth is not None and ground_truth.patient_ids is not None:
        patient_index = {}
        groups = np.array([patient_index.setdefault(ground_truth.patient_ids[c], len(patient_index))
                           for c in case_ids], dtype=np.int64)

    return AlignedData(classes, mode, case_ids, y_true, y_pred, scores, groups)
