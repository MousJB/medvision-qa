import numpy as np
import pytest

from medvision_qa.alignment import EMBEDDED, SEPARATE_FILE, align
from medvision_qa.validation import ValidationError, load_ground_truth, load_predictions


@pytest.fixture
def gt(write_csv, classes):
    return load_ground_truth(write_csv(
        "case_id,true_label,patient_id\nc1,glioma,P1\nc2,notumor,P2\nc3,pituitary,P1\n"), classes)


def preds(write_csv, classes, text):
    return load_predictions(write_csv(text), classes)


def test_row_order_does_not_matter(write_csv, classes, gt):
    a = preds(write_csv, classes, "case_id,predicted_label\nc3,pituitary\nc1,glioma\nc2,glioma\n")
    b = preds(write_csv, classes, "case_id,predicted_label\nc2,notumor\nc3,glioma\nc1,meningioma\n")
    data = align(classes, {"A": a, "B": b}, gt)
    assert data.ground_truth_mode == SEPARATE_FILE
    assert data.case_ids == ("c1", "c2", "c3")
    assert data.y_true.tolist() == [0, 2, 3]
    assert data.y_pred["A"].tolist() == [0, 0, 3]
    assert data.y_pred["B"].tolist() == [1, 2, 0]
    assert data.scores == {"A": None, "B": None}


def test_patient_groups_mapped_per_case(write_csv, classes, gt):
    a = preds(write_csv, classes, "case_id,predicted_label\nc1,glioma\nc2,notumor\nc3,glioma\n")
    data = align(classes, {"A": a}, gt)
    assert data.groups[0] == data.groups[2] != data.groups[1]


def test_missing_and_extra_cases_listed(write_csv, classes, gt):
    a = preds(write_csv, classes, "case_id,predicted_label\nc1,glioma\nc2,notumor\nc9,glioma\n")
    with pytest.raises(ValidationError) as exc:
        align(classes, {"A": a}, gt)
    values = sorted(issue.value for issue in exc.value.issues)
    assert values == ["c3", "c9"]
    assert {issue.rule for issue in exc.value.issues} == {"same_cases"}


def test_same_row_count_different_ids_not_paired(write_csv, classes, gt):
    a = preds(write_csv, classes, "case_id,predicted_label\nx1,glioma\nx2,notumor\nx3,glioma\n")
    with pytest.raises(ValidationError) as exc:
        align(classes, {"A": a}, gt)
    assert len(exc.value.issues) == 6


def test_case_ids_compared_exactly(write_csv, classes, gt):
    a = preds(write_csv, classes, "case_id,predicted_label\nC1,glioma\nc2,notumor\nc3,glioma\n")
    with pytest.raises(ValidationError):
        align(classes, {"A": a}, gt)


def test_embedded_true_label_must_match_ground_truth(write_csv, classes, gt):
    a = preds(write_csv, classes,
              "case_id,predicted_label,true_label\nc1,glioma,glioma\nc2,notumor,glioma\nc3,glioma,pituitary\n")
    with pytest.raises(ValidationError) as exc:
        align(classes, {"A": a}, gt)
    (issue,) = exc.value.issues
    assert issue.rule == "true_label_consistent" and issue.value.startswith("c2")


def test_embedded_mode(write_csv, classes):
    a = preds(write_csv, classes, "case_id,predicted_label,true_label\nc1,glioma,glioma\nc2,glioma,notumor\n")
    b = preds(write_csv, classes, "case_id,predicted_label,true_label\nc2,notumor,notumor\nc1,glioma,glioma\n")
    data = align(classes, {"A": a, "B": b})
    assert data.ground_truth_mode == EMBEDDED
    assert data.y_true.tolist() == [0, 2]
    assert data.groups is None


def test_embedded_mode_requires_true_label(write_csv, classes):
    a = preds(write_csv, classes, "case_id,predicted_label\nc1,glioma\n")
    with pytest.raises(ValidationError) as exc:
        align(classes, {"A": a})
    assert exc.value.issues[0].rule == "true_label_available"


def test_embedded_mode_labels_must_agree_between_versions(write_csv, classes):
    a = preds(write_csv, classes, "case_id,predicted_label,true_label\nc1,glioma,glioma\n")
    b = preds(write_csv, classes, "case_id,predicted_label,true_label\nc1,glioma,notumor\n")
    with pytest.raises(ValidationError) as exc:
        align(classes, {"A": a, "B": b})
    assert exc.value.issues[0].rule == "true_label_consistent"


def test_scores_aligned_in_case_order(write_csv, classes, gt):
    text = ("case_id,predicted_label,score_glioma,score_meningioma,score_notumor,score_pituitary\n"
            "c3,pituitary,0.1,0.1,0.1,0.7\nc1,glioma,0.7,0.1,0.1,0.1\nc2,notumor,0.1,0.1,0.7,0.1\n")
    data = align(classes, {"A": preds(write_csv, classes, text)}, gt)
    np.testing.assert_array_equal(data.scores["A"].argmax(axis=1), [0, 2, 3])


def test_no_version_rejected(classes, gt):
    with pytest.raises(ValueError):
        align(classes, {}, gt)
