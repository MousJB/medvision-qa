import hashlib

import pytest

from medvision_qa.classes import ClassSpec, ConfigError
from medvision_qa.validation import ValidationError, load_ground_truth, load_predictions

GT_OK = "case_id,true_label,patient_id\nc1,glioma,P1\nc2,notumor,P2\nc3,pituitary,P2\n"
PRED_OK = (
    "case_id,predicted_label,score_glioma,score_meningioma,score_notumor,score_pituitary\n"
    "c1,glioma,0.7,0.1,0.1,0.1\n"
    "c2,notumor,0.1,0.1,0.7,0.1\n"
    "c3,glioma,0.4,0.1,0.1,0.4\n"
)
SCORE_HEADER = "case_id,predicted_label,score_glioma,score_meningioma,score_notumor,score_pituitary\n"


def rules(exc_info):
    return [issue.rule for issue in exc_info.value.issues]


# --- ClassSpec -------------------------------------------------------------------------

def test_classspec_rejects_too_few_classes():
    with pytest.raises(ConfigError):
        ClassSpec(("a",))


def test_classspec_rejects_duplicates_and_bad_names():
    with pytest.raises(ConfigError):
        ClassSpec(("a", "b", "a"))
    with pytest.raises(ConfigError):
        ClassSpec(("a", "b c"))


def test_classspec_rejects_string_positive_instead_of_list():
    # Une chaîne itérée caractère par caractère serait un bug silencieux.
    with pytest.raises(ConfigError, match="liste"):
        ClassSpec(("ab", "cd"), "ab")


def test_classspec_rejects_unknown_or_all_positive():
    with pytest.raises(ConfigError):
        ClassSpec(("a", "b"), ("z",))
    with pytest.raises(ConfigError):
        ClassSpec(("a", "b"), ("a", "b"))


def test_classspec_positive_indices(classes):
    assert classes.positive_indices == (0, 1, 3)


# --- Vérité terrain --------------------------------------------------------------------

def test_ground_truth_valid(write_csv, classes):
    path = write_csv(GT_OK)
    gt = load_ground_truth(path, classes)
    assert gt.labels == {"c1": "glioma", "c2": "notumor", "c3": "pituitary"}
    assert gt.patient_ids == {"c1": "P1", "c2": "P2", "c3": "P2"}
    assert gt.source.n_rows == 3
    assert gt.source.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "unique_case_id" in gt.source.checks


def test_ground_truth_without_patient_id(write_csv, classes):
    gt = load_ground_truth(write_csv("case_id,true_label\nc1,glioma\n"), classes)
    assert gt.patient_ids is None


def test_utf8_bom_accepted(write_csv, classes):
    gt = load_ground_truth(write_csv("﻿" + GT_OK), classes)
    assert set(gt.labels) == {"c1", "c2", "c3"}


def test_crlf_line_endings_accepted(write_csv, classes):
    gt = load_ground_truth(write_csv(GT_OK.replace("\n", "\r\n")), classes)
    assert gt.source.n_rows == 3


def test_non_utf8_rejected(write_csv, classes):
    path = write_csv("case_id,true_label\nc1,glioma\nc2,méningiome\n", encoding="latin-1")
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(path, classes)
    assert rules(exc) == ["encoding_utf8"]


def test_empty_file_rejected(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv(""), classes)
    assert rules(exc) == ["header_present"]


def test_header_only_rejected(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label\n"), classes)
    assert rules(exc) == ["no_data_rows"]


def test_missing_required_column(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id\nc1\n"), classes)
    assert "required_columns" in rules(exc)


def test_unknown_column_rejected_but_meta_allowed(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label,image_path\nc1,glioma,a.png\n"), classes)
    assert rules(exc) == ["no_unknown_columns"]
    gt = load_ground_truth(write_csv("case_id,true_label,meta_image_path\nc1,glioma,a.png\n"), classes)
    assert gt.labels == {"c1": "glioma"}


def test_duplicate_column_rejected(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label,true_label\nc1,glioma,glioma\n"), classes)
    assert "no_duplicate_columns" in rules(exc)


def test_duplicate_case_id_reports_both_lines(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label\nc1,glioma\nc2,notumor\nc1,glioma\n"), classes)
    (issue,) = exc.value.issues
    assert issue.rule == "unique_case_id"
    assert issue.line == 4 and "ligne 2" in issue.message


def test_empty_case_id_and_label(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label\n,glioma\nc2,\n"), classes)
    assert rules(exc) == ["required_values_present", "required_values_present"]
    assert [i.line for i in exc.value.issues] == [2, 3]


def test_surrounding_whitespace_not_stripped(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label\nc1, glioma\n"), classes)
    assert "no_surrounding_whitespace" in rules(exc)


def test_label_is_case_sensitive(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label\nc1,Glioma\n"), classes)
    (issue,) = exc.value.issues
    assert issue.rule == "labels_declared" and issue.value == "Glioma"


def test_empty_line_rejected_not_skipped(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label\nc1,glioma\n\nc2,notumor\n"), classes)
    (issue,) = exc.value.issues
    assert issue.rule == "no_empty_lines" and issue.line == 3


def test_wrong_field_count(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label\nc1,glioma,extra\nc2\n"), classes)
    assert rules(exc) == ["field_count", "field_count"]


def test_malformed_quoting(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv('case_id,true_label\n"c1"x,glioma\n'), classes)
    assert rules(exc) == ["csv_syntax"]


def test_empty_patient_id_rejected(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv("case_id,true_label,patient_id\nc1,glioma,\n"), classes)
    assert rules(exc) == ["required_values_present"]


def test_all_errors_collected_in_one_pass(write_csv, classes):
    text = "case_id,true_label\nc1,glioma\nc1,unknown\n,notumor\n"
    with pytest.raises(ValidationError) as exc:
        load_ground_truth(write_csv(text), classes)
    assert sorted(rules(exc)) == ["labels_declared", "required_values_present", "unique_case_id"]
    assert "3 problème(s)" in str(exc.value)


# --- Prédictions -----------------------------------------------------------------------

def test_predictions_valid_with_scores(write_csv, classes):
    preds = load_predictions(write_csv(PRED_OK), classes)
    assert preds.predicted["c3"] == "glioma"
    assert preds.scores["c1"] == (0.7, 0.1, 0.1, 0.1)
    assert preds.true_labels is None
    assert any(check.startswith("score_sum_to_one") for check in preds.source.checks)


def test_score_columns_mapped_by_name_not_position(write_csv, classes):
    text = ("case_id,score_pituitary,score_notumor,score_meningioma,score_glioma,predicted_label\n"
            "c1,0.1,0.2,0.3,0.4,glioma\n")
    preds = load_predictions(write_csv(text), classes)
    assert preds.scores["c1"] == (0.4, 0.3, 0.2, 0.1)  # ordre de ClassSpec


def test_predictions_without_scores(write_csv, classes):
    preds = load_predictions(write_csv("case_id,predicted_label\nc1,glioma\n"), classes)
    assert preds.scores is None


def test_partial_scores_rejected(write_csv, classes):
    text = "case_id,predicted_label,score_glioma,score_notumor\nc1,glioma,0.6,0.4\n"
    with pytest.raises(ValidationError) as exc:
        load_predictions(write_csv(text), classes)
    assert rules(exc) == ["score_columns_complete", "score_columns_complete"]


def test_score_for_undeclared_class_rejected(write_csv, classes):
    text = SCORE_HEADER.rstrip("\n") + ",score_other\nc1,glioma,0.7,0.1,0.1,0.1,0.0\n"
    with pytest.raises(ValidationError) as exc:
        load_predictions(write_csv(text), classes)
    assert rules(exc) == ["score_columns_complete"]


@pytest.mark.parametrize("value, rule", [
    ("nan", "score_numeric"),
    ("inf", "score_numeric"),
    ("1_0", "score_numeric"),
    ("abc", "score_numeric"),
    ("1e999", "score_finite"),
    ("1.5", "score_in_bounds"),
    ("-0.1", "score_in_bounds"),
])
def test_invalid_score_values(write_csv, classes, value, rule):
    text = SCORE_HEADER + f"c1,glioma,{value},0.1,0.1,0.1\n"
    with pytest.raises(ValidationError) as exc:
        load_predictions(write_csv(text), classes)
    assert rules(exc) == [rule]


def test_empty_score_value_rejected(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_predictions(write_csv(SCORE_HEADER + "c1,glioma,,0.5,0.25,0.25\n"), classes)
    assert rules(exc) == ["required_values_present"]


def test_scores_must_sum_to_one_within_tolerance(write_csv, classes):
    path = write_csv(SCORE_HEADER + "c1,glioma,0.7,0.1,0.1,0.1005\n")
    load_predictions(path, classes, probability_sum_tolerance=1e-3)
    with pytest.raises(ValidationError) as exc:
        load_predictions(path, classes, probability_sum_tolerance=1e-4)
    assert rules(exc) == ["score_sum_to_one"]


def test_invalid_tolerance_rejected(write_csv, classes):
    with pytest.raises(ValueError):
        load_predictions(write_csv(PRED_OK), classes, probability_sum_tolerance=0)


def test_predicted_label_must_be_argmax(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_predictions(write_csv(SCORE_HEADER + "c1,notumor,0.7,0.1,0.1,0.1\n"), classes)
    assert rules(exc) == ["predicted_is_argmax"]


def test_tie_accepts_any_tied_class(write_csv, classes):
    for label in ("glioma", "pituitary"):
        load_predictions(write_csv(SCORE_HEADER + f"c1,{label},0.4,0.1,0.1,0.4\n"), classes)


def test_embedded_true_label_validated(write_csv, classes):
    preds = load_predictions(write_csv("case_id,predicted_label,true_label\nc1,glioma,notumor\n"), classes)
    assert preds.true_labels == {"c1": "notumor"}
    with pytest.raises(ValidationError) as exc:
        load_predictions(write_csv("case_id,predicted_label,true_label\nc1,glioma,tumour\n"), classes)
    assert rules(exc) == ["labels_declared"]


def test_unknown_predicted_label(write_csv, classes):
    with pytest.raises(ValidationError) as exc:
        load_predictions(write_csv("case_id,predicted_label\nc1,cancer\n"), classes)
    assert rules(exc) == ["labels_declared"]
