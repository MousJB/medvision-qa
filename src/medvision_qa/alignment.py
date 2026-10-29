"""Alignement explicite des cas par ``case_id`` (docs/data_format.md § 5-6).

Les ensembles de ``case_id`` doivent être identiques : aucun appariement par position,
aucune intersection implicite.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from medvision_qa.classes import ClassSpec
from medvision_qa.validation import GroundTruth, Predictions, ValidationError, ValidationIssue

SEPARATE_FILE = "separate_file"
EMBEDDED = "embedded"


@dataclass(frozen=True)
class AlignedData:
    """Données alignées, triées par ``case_id`` pour ne pas dépendre de l'ordre des fichiers.

    ``y_true`` / ``y_pred`` : indices dans ``classes.order``. ``scores[v]`` : matrice
    (n, k) ou None. ``groups`` : indice de patient par cas, ou None.
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
                                      f"cas présent dans {reference_name} mais absent ici",
                                      column="case_id", value=case_id))
    for case_id in sorted(other_ids - reference_ids):
        issues.append(ValidationIssue(other_name, "same_cases",
                                      f"cas absent de {reference_name}",
                                      column="case_id", value=case_id))


def _compare_labels(reference_name, reference, other_name, other, issues):
    for case_id in sorted(reference.keys() & other.keys()):
        if reference[case_id] != other[case_id]:
            issues.append(ValidationIssue(
                other_name, "true_label_consistent",
                f"true_label différent de celui de {reference_name} ({reference[case_id]!r})",
                column="true_label", value=f"{case_id}: {other[case_id]}"))


def align(classes: ClassSpec, predictions: Mapping[str, Predictions],
          ground_truth: GroundTruth | None = None) -> AlignedData:
    """Aligne une ou plusieurs versions (``{"A": ..., "B": ...}``) sur la vérité terrain.

    ``ground_truth`` fourni : mode ``separate_file``. Absent : mode ``embedded``, chaque
    fichier de prédictions doit alors contenir ``true_label``.
    """
    if not predictions:
        raise ValueError("Au moins une version de prédictions est requise.")
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
                                "mode embedded : colonne true_label requise sans fichier de "
                                "vérité terrain", column="true_label")
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
