"""Local web interface (FastAPI + Jinja2): file upload, evaluation, history, report.

Start: ``python -m medvision_qa.web`` (listens on 127.0.0.1 only). Every page exists in
English and Japanese (``?lang=ja``); each evaluation produces both reports.

Security (spec § 12): file names filtered and without path, file size and count limited,
no file executed or deserialised other than as CSV/TOML, evaluation identifiers validated,
strict CSP headers, no JavaScript, no network calls.
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
from markupsafe import Markup

from medvision_qa.classes import ConfigError
from medvision_qa.evaluation import run_evaluation
from medvision_qa.history import (COMPLETED, REJECTED, EvaluationRecord, History, dump_message,
                                  load_message, load_messages, load_text)
from medvision_qa.i18n import DEFAULT_LANGUAGE, LANGUAGES, Text, msg, t
from medvision_qa.report import write_report
from medvision_qa.validation import ValidationError

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_DATA_FILES = 4
MAX_ERRORS_SHOWN = 50
FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "synthetic_demo"
EXAMPLE_FILES = ("config.toml", "config.ja.toml", "ground_truth.csv", "preds_v1.csv", "preds_v2.csv")
REPORT_FILES = {"en": "report.html", "ja": "report.ja.html"}

APP_CSP = ("default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
           "base-uri 'none'; frame-ancestors 'none'")
REPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'"

_templates = Environment(loader=PackageLoader("medvision_qa", "templates"),
                         autoescape=select_autoescape(default=True, default_for_string=True),
                         undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)


class UploadRejected(Exception):
    def __init__(self, errors: list[Text], status_code=400):
        super().__init__("; ".join(str(e) for e in errors))
        self.errors = list(errors)
        self.status_code = status_code


def _language(value: str | None) -> str:
    return value if value in LANGUAGES else DEFAULT_LANGUAGE


def _page(name: str, lang: str, status_code: int = 200, **context) -> HTMLResponse:
    def url(path: str) -> str:
        return path if lang == DEFAULT_LANGUAGE else f"{path}?lang={lang}"

    def state(value: str) -> Markup:
        return Markup('<span class="state {}">{}</span>').format(value, t(f"state.{value}", lang))

    html = _templates.get_template(name).render(
        lang=lang, _=lambda key, **params: t(key, lang, **params), state=state,
        tr=lambda value: value.render(lang) if hasattr(value, "render") else value, url=url, **context)
    return HTMLResponse(html, status_code=status_code)


def _not_found(lang: str) -> HTMLResponse:
    return _page("web_not_found.html.j2", lang, status_code=404, path="/")


def _save_uploads(workspace: Path, config: UploadFile | None, data_files: list[UploadFile]) -> Path:
    """Checks and stores the files; returns the path of the configuration."""
    data_files = [f for f in data_files if f.filename]
    errors = []
    if config is None or not config.filename:
        errors.append(msg("web.no_config"))
    if not data_files:
        errors.append(msg("web.no_csv"))
    if len(data_files) > MAX_DATA_FILES:
        errors.append(msg("web.too_many_files", n=len(data_files), max=MAX_DATA_FILES))
    names = []
    uploads = [(config, ".toml")] if config is not None and config.filename else []
    uploads += [(f, ".csv") for f in data_files]
    for upload, extension in uploads:
        name = upload.filename
        if not FILENAME_PATTERN.fullmatch(name):
            errors.append(msg("web.bad_filename", name=repr(name)))
        elif not name.lower().endswith(extension):
            errors.append(msg("web.bad_extension", name=repr(name), extension=extension))
        names.append(name)
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        errors.append(msg("web.duplicate_names", names=str(duplicates)))
    if errors:
        raise UploadRejected(errors)

    workspace.mkdir(parents=True)
    for upload in [config] + data_files:
        content = upload.file.read(MAX_FILE_BYTES + 1)
        if len(content) > MAX_FILE_BYTES:
            raise UploadRejected([msg("web.too_large", name=repr(upload.filename),
                                      mb=MAX_FILE_BYTES // (1024 * 1024))], 413)
        (workspace / upload.filename).write_bytes(content)
    return workspace / config.filename


def _criteria_summary(result) -> str:
    return json.dumps([{"id": r.criterion.id, "description": r.criterion.description,
                        "quantity": r.quantity, "state": r.state, "reason": dump_message(r.reason)}
                       for r in result.decision.criteria], ensure_ascii=False)


def _rejection_errors(exc: ConfigError | ValidationError) -> list:
    """Messages to show and store: ``ValidationIssue`` or ``Text``, both renderable in any language."""
    if isinstance(exc, ValidationError):
        return list(exc.issues)
    return [msg("web.invalid_config", error=exc.text)]


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

    def index(lang, errors=(), status_code=200):
        return _page("web_index.html.j2", lang, status_code=status_code, path="/", errors=list(errors),
                     history=history.recent(), load_messages=load_messages, example_files=EXAMPLE_FILES,
                     max_files=MAX_DATA_FILES, max_mb=MAX_FILE_BYTES // (1024 * 1024))

    @app.get("/", response_class=HTMLResponse)
    def home(lang: str | None = None):
        return index(_language(lang))

    @app.post("/evaluations")
    def create_evaluation(lang: str | None = None, config: UploadFile = File(None),
                          data_files: list[UploadFile] = File([])):
        lang = _language(lang)
        run_id = str(uuid.uuid4())
        workspace = runs_dir / run_id
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        completed = False
        try:
            config_path = _save_uploads(workspace, config, data_files)
            result = run_evaluation(config_path, run_id=run_id)
            for report_lang, name in REPORT_FILES.items():
                write_report(result, workspace / name, lang=report_lang)
            versions = result.config.versions
            history.add(EvaluationRecord(
                run_id=run_id, created_at_utc=created, status=COMPLETED, title=result.config.title,
                decision=result.decision.state, decision_reason=json.dumps(dump_message(result.decision.reason)),
                config_sha256=result.config.sha256, n_cases=result.data.n_cases,
                version_a=versions["A"].id, version_b=versions["B"].id if "B" in versions else None,
                criteria_json=_criteria_summary(result)))
            completed = True
            suffix = "" if lang == DEFAULT_LANGUAGE else f"?lang={lang}"
            return RedirectResponse(f"/evaluations/{run_id}{suffix}", status_code=303)
        except UploadRejected as exc:
            return index(lang, exc.errors, exc.status_code)
        except (ConfigError, ValidationError) as exc:
            errors = _rejection_errors(exc)
            history.add(EvaluationRecord(run_id=run_id, created_at_utc=created, status=REJECTED,
                                         error=json.dumps([dump_message(e) for e in errors], ensure_ascii=False)))
            shown = errors[:MAX_ERRORS_SHOWN]
            if len(errors) > MAX_ERRORS_SHOWN:
                shown.append(msg("issue.more", n=len(errors) - MAX_ERRORS_SHOWN))
            return index(lang, [msg("web.rejected")] + shown, 422)
        finally:
            if not completed and workspace.exists():
                shutil.rmtree(workspace)  # keep no data from a rejected evaluation

    def completed_record(run_id: str):
        if not RUN_ID_PATTERN.fullmatch(run_id):
            return None
        record = history.get(run_id)
        if record is None or record.status != COMPLETED or not (runs_dir / run_id / "report.html").is_file():
            return None
        return record

    @app.get("/evaluations/{run_id}", response_class=HTMLResponse)
    def show_evaluation(run_id: str, lang: str | None = None):
        lang = _language(lang)
        record = completed_record(run_id)
        if record is None:
            return _not_found(lang)
        criteria = [dict(c, reason=load_message(c["reason"])) for c in json.loads(record.criteria_json)]
        return _page("web_evaluation.html.j2", lang, path=f"/evaluations/{run_id}", record=record,
                     decision_reason=load_text(record.decision_reason), criteria=criteria)

    def report_file(run_id: str, lang: str) -> Path:
        path = runs_dir / run_id / REPORT_FILES[lang]
        return path if path.is_file() else runs_dir / run_id / REPORT_FILES[DEFAULT_LANGUAGE]

    @app.get("/evaluations/{run_id}/report")
    def view_report(run_id: str, lang: str | None = None):
        lang = _language(lang)
        if completed_record(run_id) is None:
            return _not_found(lang)
        return FileResponse(report_file(run_id, lang), media_type="text/html; charset=utf-8",
                            headers={"Content-Security-Policy": REPORT_CSP})

    @app.get("/evaluations/{run_id}/report/download")
    def download_report(run_id: str, lang: str | None = None):
        lang = _language(lang)
        if completed_record(run_id) is None:
            return _not_found(lang)
        suffix = "" if lang == DEFAULT_LANGUAGE else f".{lang}"
        return FileResponse(report_file(run_id, lang), media_type="text/html; charset=utf-8",
                            filename=f"VVR-{run_id}{suffix}.html", headers={"Content-Security-Policy": REPORT_CSP})

    @app.get("/examples/{name}")
    def example_file(name: str):
        if name not in EXAMPLE_FILES or not (EXAMPLE_DIR / name).is_file():
            return _not_found(DEFAULT_LANGUAGE)
        media = "text/csv" if name.endswith(".csv") else "application/toml"
        return Response((EXAMPLE_DIR / name).read_bytes(), media_type=f"{media}; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    return app


def main(argv=None) -> None:
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(prog="python -m medvision_qa.web",
                                     description="MedVision QA local web interface (127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", type=Path, default=Path("medvision_data"),
                        help="folder for evaluations and the SQLite history (default: ./medvision_data)")
    args = parser.parse_args(argv)
    print(f"MedVision QA: http://127.0.0.1:{args.port}  (data: {args.data_dir.resolve()})")
    uvicorn.run(create_app(args.data_dir), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
