"""Interface web locale (FastAPI + Jinja2) : import des fichiers, évaluation, historique, rapport.

Lancement : ``python -m medvision_qa.web`` (écoute uniquement sur 127.0.0.1).

Sécurité (spec § 12) : noms de fichiers filtrés et sans chemin, taille et nombre de fichiers
limités, aucun fichier exécuté ni désérialisé autrement qu'en CSV/TOML, identifiants
d'évaluation validés, en-têtes CSP stricts, pas de JavaScript, pas d'appel réseau.
"""

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from medvision_qa.classes import ConfigError
from medvision_qa.evaluation import run_evaluation
from medvision_qa.history import COMPLETED, REJECTED, EvaluationRecord, History
from medvision_qa.report import write_report
from medvision_qa.validation import ValidationError

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_DATA_FILES = 4
MAX_ERRORS_SHOWN = 50
FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "synthetic_demo"
EXAMPLE_FILES = ("config.toml", "ground_truth.csv", "preds_v1.csv", "preds_v2.csv")

APP_CSP = ("default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
           "base-uri 'none'; frame-ancestors 'none'")
REPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'"

_templates = Environment(loader=PackageLoader("medvision_qa", "templates"),
                         autoescape=select_autoescape(default=True, default_for_string=True),
                         undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


class UploadRejected(Exception):
    def __init__(self, errors, status_code=400):
        super().__init__("; ".join(errors))
        self.errors = list(errors)
        self.status_code = status_code


def _page(name: str, status_code: int = 200, **context) -> HTMLResponse:
    return HTMLResponse(_templates.get_template(name).render(**context), status_code=status_code)


def _not_found() -> HTMLResponse:
    return _page("web_not_found.html.j2", status_code=404)


def _save_uploads(workspace: Path, config: UploadFile | None, data_files: list[UploadFile]) -> Path:
    """Vérifie et enregistre les fichiers ; retourne le chemin de la configuration."""
    data_files = [f for f in data_files if f.filename]
    errors = []
    if config is None or not config.filename:
        errors.append("Aucun fichier de configuration (.toml) fourni.")
    if not data_files:
        errors.append("Aucun fichier CSV fourni.")
    if len(data_files) > MAX_DATA_FILES:
        errors.append(f"{len(data_files)} fichiers CSV fournis ; maximum {MAX_DATA_FILES}.")
    names = []
    uploads = [(config, ".toml")] if config is not None and config.filename else []
    uploads += [(f, ".csv") for f in data_files]
    for upload, extension in uploads:
        name = upload.filename
        if not FILENAME_PATTERN.fullmatch(name):
            errors.append(f"Nom de fichier refusé : {name!r} (lettres, chiffres, . _ - ; sans dossier).")
        elif not name.lower().endswith(extension):
            errors.append(f"{name!r} : extension {extension} attendue.")
        names.append(name)
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        errors.append(f"Noms de fichiers en double : {duplicates}.")
    if errors:
        raise UploadRejected(errors)

    workspace.mkdir(parents=True)
    for upload in [config] + data_files:
        content = upload.file.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise UploadRejected([f"{upload.filename!r} dépasse {MAX_FILE_BYTES // (1024 * 1024)} Mo."], 413)
        (workspace / upload.filename).write_bytes(content)
    return workspace / config.filename


def _criteria_summary(result) -> str:
    return json.dumps([{"id": r.criterion.id, "description": r.criterion.description,
                        "quantity": r.quantity, "state": r.state, "reason": r.reason}
                       for r in result.decision.criteria], ensure_ascii=False)


def create_app(data_dir) -> FastAPI:
    data_dir = Path(data_dir).resolve()
    runs_dir = data_dir / "runs"
    history = History(data_dir / "history.sqlite")
    app = FastAPI(title="MedVision QA", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", APP_CSP)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    def index(errors=(), status_code=200):
        return _page("web_index.html.j2", status_code=status_code, errors=list(errors),
                     history=history.recent(), example_files=EXAMPLE_FILES,
                     max_files=MAX_DATA_FILES, max_mb=MAX_FILE_BYTES // (1024 * 1024))

    @app.get("/", response_class=HTMLResponse)
    def home():
        return index()

    @app.post("/evaluations")
    def create_evaluation(config: UploadFile = File(None), data_files: list[UploadFile] = File([])):
        run_id = str(uuid.uuid4())
        workspace = runs_dir / run_id
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        completed = False
        try:
            config_path = _save_uploads(workspace, config, data_files)
            result = run_evaluation(config_path, run_id=run_id)
            write_report(result, workspace / "report.html")
            versions = result.config.versions
            history.add(EvaluationRecord(
                run_id=run_id, created_at_utc=created, status=COMPLETED, title=result.config.title,
                decision=result.decision.state, decision_reason=result.decision.reason,
                config_sha256=result.config.sha256, n_cases=result.data.n_cases,
                version_a=versions["A"].id, version_b=versions["B"].id if "B" in versions else None,
                criteria_json=_criteria_summary(result)))
            completed = True
            return RedirectResponse(f"/evaluations/{run_id}", status_code=303)
        except UploadRejected as exc:
            return index(exc.errors, exc.status_code)
        except (ConfigError, ValidationError) as exc:
            errors = ([str(issue) for issue in exc.issues] if isinstance(exc, ValidationError)
                      else [f"Configuration invalide : {exc}"])
            history.add(EvaluationRecord(run_id=run_id, created_at_utc=created, status=REJECTED,
                                         error="\n".join(errors)))
            shown = errors[:MAX_ERRORS_SHOWN]
            if len(errors) > MAX_ERRORS_SHOWN:
                shown.append(f"... et {len(errors) - MAX_ERRORS_SHOWN} autre(s) problème(s).")
            return index(["Évaluation refusée, aucun rapport produit."] + shown, 422)
        finally:
            if not completed and workspace.exists():
                shutil.rmtree(workspace)  # ne pas conserver de données d'une évaluation refusée

    def completed_record(run_id: str):
        if not RUN_ID_PATTERN.fullmatch(run_id):
            return None
        record = history.get(run_id)
        if record is None or record.status != COMPLETED or not (runs_dir / run_id / "report.html").is_file():
            return None
        return record

    @app.get("/evaluations/{run_id}", response_class=HTMLResponse)
    def show_evaluation(run_id: str):
        record = completed_record(run_id)
        if record is None:
            return _not_found()
        return _page("web_evaluation.html.j2", record=record, criteria=json.loads(record.criteria_json))

    @app.get("/evaluations/{run_id}/report")
    def view_report(run_id: str):
        if completed_record(run_id) is None:
            return _not_found()
        return FileResponse(runs_dir / run_id / "report.html", media_type="text/html; charset=utf-8",
                            headers={"Content-Security-Policy": REPORT_CSP})

    @app.get("/evaluations/{run_id}/report/download")
    def download_report(run_id: str):
        if completed_record(run_id) is None:
            return _not_found()
        return FileResponse(runs_dir / run_id / "report.html", media_type="text/html; charset=utf-8",
                            filename=f"VVR-{run_id}.html", headers={"Content-Security-Policy": REPORT_CSP})

    @app.get("/examples/{name}")
    def example_file(name: str):
        if name not in EXAMPLE_FILES or not (EXAMPLE_DIR / name).is_file():
            return _not_found()
        media = "text/csv" if name.endswith(".csv") else "application/toml"
        return Response((EXAMPLE_DIR / name).read_bytes(), media_type=f"{media}; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    return app


def main(argv=None) -> None:
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(prog="python -m medvision_qa.web",
                                     description="Interface web locale de MedVision QA (127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", type=Path, default=Path("medvision_data"),
                        help="dossier des évaluations et de l'historique SQLite (défaut : ./medvision_data)")
    args = parser.parse_args(argv)
    print(f"MedVision QA : http://127.0.0.1:{args.port}  (données : {args.data_dir.resolve()})")
    uvicorn.run(create_app(args.data_dir), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
