"""Local history of evaluations (SQLite, standard library).

Rejected evaluations (invalid configuration or data) are recorded too, with their errors:
a refusal is information worth tracing. Messages are stored in structured form (catalog key
and parameters) so the history can be shown in any supported language.
"""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from medvision_qa.i18n import Text, raw
from medvision_qa.validation import ValidationIssue

COMPLETED = "completed"
REJECTED = "rejected"

SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    run_id          TEXT PRIMARY KEY,
    created_at_utc  TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('completed', 'rejected')),
    title           TEXT,
    decision        TEXT,
    decision_reason TEXT,
    config_sha256   TEXT,
    n_cases         INTEGER,
    version_a       TEXT,
    version_b       TEXT,
    criteria_json   TEXT,
    error           TEXT
)
"""


@dataclass(frozen=True)
class EvaluationRecord:
    run_id: str
    created_at_utc: str
    status: str
    title: str | None = None
    decision: str | None = None
    decision_reason: str | None = None  # JSON of dump_message(Text)
    config_sha256: str | None = None
    n_cases: int | None = None
    version_a: str | None = None
    version_b: str | None = None
    criteria_json: str | None = None  # [{id, description, quantity, state, reason}]
    error: str | None = None  # JSON list of dump_message(...)


FIELDS = tuple(EvaluationRecord.__dataclass_fields__)


def dump_message(message: Text | ValidationIssue) -> dict:
    if isinstance(message, ValidationIssue):
        return {"issue": {"file": message.file, "rule": message.rule, "message": message.message.to_dict(),
                          "line": message.line, "column": message.column, "value": message.value}}
    return {"text": message.to_dict()}


def load_message(data) -> Text | ValidationIssue:
    """Inverse of ``dump_message``. A plain string (older history) is shown as is."""
    if isinstance(data, str):
        return raw(data)
    if "issue" in data:
        issue = dict(data["issue"])
        issue["message"] = Text.from_dict(issue["message"])
        return ValidationIssue(**issue)
    return Text.from_dict(data["text"])


def _json_or_none(value: str):
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def load_text(value: str | None) -> Text | ValidationIssue | None:
    """A single stored message (e.g. ``decision_reason``)."""
    if value is None:
        return None
    data = _json_or_none(value)
    return load_message(data) if isinstance(data, dict) else raw(value)


def load_messages(value: str | None) -> list:
    """A stored list of messages (``error``)."""
    if not value:
        return []
    data = _json_or_none(value)
    if not isinstance(data, list):
        return [raw(line) for line in value.splitlines()]
    return [load_message(item) for item in data]


class History:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute(SCHEMA)

    def _connect(self):
        return sqlite3.connect(self.path)

    def add(self, record: EvaluationRecord) -> None:
        placeholders = ", ".join("?" for _ in FIELDS)
        with closing(self._connect()) as conn, conn:
            conn.execute(f"INSERT INTO evaluations ({', '.join(FIELDS)}) VALUES ({placeholders})",
                         [getattr(record, f) for f in FIELDS])

    def get(self, run_id: str) -> EvaluationRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute(f"SELECT {', '.join(FIELDS)} FROM evaluations WHERE run_id = ?",
                               (run_id,)).fetchone()
        return EvaluationRecord(*row) if row else None

    def recent(self, limit: int = 50) -> list[EvaluationRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(f"SELECT {', '.join(FIELDS)} FROM evaluations "
                                "ORDER BY created_at_utc DESC, rowid DESC LIMIT ?", (limit,)).fetchall()
        return [EvaluationRecord(*row) for row in rows]
