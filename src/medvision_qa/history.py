"""Historique local des évaluations (SQLite, bibliothèque standard).

Les évaluations rejetées (configuration ou données invalides) sont aussi enregistrées,
avec le résumé des erreurs : un refus est une information à tracer.
"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

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
    decision_reason: str | None = None
    config_sha256: str | None = None
    n_cases: int | None = None
    version_a: str | None = None
    version_b: str | None = None
    criteria_json: str | None = None  # [{id, description, state, reason}]
    error: str | None = None


FIELDS = tuple(EvaluationRecord.__dataclass_fields__)


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
