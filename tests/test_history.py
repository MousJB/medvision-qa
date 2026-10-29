import sqlite3

import pytest

from medvision_qa.history import (COMPLETED, REJECTED, EvaluationRecord, History, dump_message,
                                  load_message, load_messages, load_text)
from medvision_qa.i18n import msg
from medvision_qa.validation import ValidationIssue


def test_add_get_recent(tmp_path):
    history = History(tmp_path / "sub" / "h.sqlite")
    first = EvaluationRecord("id-1", "2026-10-29T01:00:00+00:00", COMPLETED, title="t1", decision="SATISFIED",
                             n_cases=10, version_a="v1", criteria_json="[]")
    second = EvaluationRecord("id-2", "2026-10-29T02:00:00+00:00", REJECTED, error="[same_cases] ...")
    history.add(first)
    history.add(second)
    assert history.get("id-1") == first
    assert history.get("missing") is None
    assert [r.run_id for r in history.recent()] == ["id-2", "id-1"]
    assert [r.run_id for r in history.recent(limit=1)] == ["id-2"]


def test_persists_across_instances(tmp_path):
    History(tmp_path / "h.sqlite").add(EvaluationRecord("id-1", "2026-10-29T01:00:00+00:00", COMPLETED))
    assert History(tmp_path / "h.sqlite").get("id-1").status == COMPLETED


def test_invalid_status_rejected_by_schema(tmp_path):
    history = History(tmp_path / "h.sqlite")
    with pytest.raises(sqlite3.IntegrityError):
        history.add(EvaluationRecord("id-1", "2026-10-29T01:00:00+00:00", "maybe"))


def test_duplicate_run_id_rejected(tmp_path):
    history = History(tmp_path / "h.sqlite")
    record = EvaluationRecord("id-1", "2026-10-29T01:00:00+00:00", COMPLETED)
    history.add(record)
    with pytest.raises(sqlite3.IntegrityError):
        history.add(record)


def test_values_are_parameterised(tmp_path):
    history = History(tmp_path / "h.sqlite")
    nasty = "x'); DROP TABLE evaluations; --"
    history.add(EvaluationRecord(nasty, "2026-10-29T01:00:00+00:00", REJECTED, error=nasty))
    assert history.get(nasty).error == nasty


def test_messages_round_trip_and_render_in_both_languages():
    reason = msg("dec.ni_inconclusive", ci=msg("dec.ci", lower="-0.0100", upper="0.0400"), m="-0.0200")
    issue = ValidationIssue("b.csv", "same_cases", msg("val.case_extra", reference="gt.csv"),
                            column="case_id", value="c9")
    for message in (reason, issue):
        loaded = load_message(dump_message(message))
        assert loaded == message
        assert loaded.render("en") == message.render("en") and loaded.render("ja") == message.render("ja")
    assert "非劣性" in reason.render("ja")


def test_older_plain_text_history_still_readable():
    assert load_text("criterion(s) not satisfied: ['C1']").render("ja") == "criterion(s) not satisfied: ['C1']"
    assert [m.render() for m in load_messages("line 1\nline 2")] == ["line 1", "line 2"]
    assert load_messages(None) == [] and load_text(None) is None
