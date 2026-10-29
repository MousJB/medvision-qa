"""Local web interface (FastAPI + Jinja2): file upload, evaluation, history, report.

Start: ``python -m medvision_qa.web`` (listens on 127.0.0.1 only). Every page exists in
English and Japanese (``?lang=ja``); each evaluation produces both reports.

Public demo mode (``create_app(public_demo=True)``, used by the Vercel deployment in
``app.py``): nothing is stored. Uploads are evaluated in a temporary folder deleted before
the response is sent, there is no shared history, and the reports are returned inside the
result page. The bundled evaluations (``/demo/...``) are computed by the server, never
pre-written.

Security (spec § 12): file names filtered and without path, file size and count limited,
no file executed or deserialised other than as CSV/TOML, evaluation identifiers validated,
strict CSP headers, no JavaScript, no network calls.
"""

import base64
import functools
import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from medvision_qa.classes import ConfigError
from medvision_qa.config import load_config
from medvision_qa.evaluation import EvaluationResult, run_evaluation
from medvision_qa.history import (COMPLETED, REJECTED, EvaluationRecord, History, dump_message,
                                  load_message, load_messages, load_text)
from medvision_qa.i18n import DEFAULT_LANGUAGE, LANGUAGES, Text, msg, t
from medvision_qa.report import render_report, write_report
from medvision_qa.validation import ValidationError

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_DATA_FILES = 4
MAX_ERRORS_SHOWN = 50
FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

GITHUB_URL = "https://github.com/MousJB/medvision-qa"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_FILES = ("config.toml", "config.ja.toml", "ground_truth.csv", "preds_v1.csv", "preds_v2.csv")
REPORT_FILES = {"en": "report.html", "ja": "report.ja.html"}

# Evaluations anyone can run in one click: configuration path (from the project root) and
# the note that says where the predictions come from. Both are committed in the repository.
DEMOS = {
    "synthetic": ("examples/synthetic_demo/config.toml", "web.demo_synthetic_note"),
    "brain-mri": ("experiments/brain_mri/figshare_eval/config.toml", "web.demo_mri_note"),
}

# Public demo: the hosting platform rejects request bodies above 4.5 MB, and the bootstrap
# is capped so that a single upload cannot hold the server for minutes.
PUBLIC_MAX_FILE_BYTES = 4 * 1024 * 1024
PUBLIC_MAX_RESAMPLES = 2000

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


def _save_uploads(workspace: Path, config: UploadFile | None, data_files: list[UploadFile],
                  max_bytes: int | None = None) -> Path:
    """Checks and stores the files; returns the path of the configuration."""
    max_bytes = MAX_FILE_BYTES if max_bytes is None else max_bytes
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
        content = upload.file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise UploadRejected([msg("web.too_large", name=repr(upload.filename),
                                      mb=max_bytes // (1024 * 1024))], 413)
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


def _shown_errors(errors: list) -> list:
    shown = errors[:MAX_ERRORS_SHOWN]
    if len(errors) > MAX_ERRORS_SHOWN:
        shown.append(msg("issue.more", n=len(errors) - MAX_ERRORS_SHOWN))
    return shown


def _summary(result: EvaluationResult) -> tuple[EvaluationRecord, list[dict]]:
    """What the result page shows, for a result that is not stored in the history."""
    versions = result.config.versions
    record = EvaluationRecord(
        run_id=result.run.run_id, created_at_utc=result.run.started_at_utc, status=COMPLETED,
        title=result.config.title, decision=result.decision.state, config_sha256=result.config.sha256,
        n_cases=result.data.n_cases, version_a=versions["A"].id,
        version_b=versions["B"].id if "B" in versions else None)
    criteria = [{"id": r.criterion.id, "description": r.criterion.description, "quantity": r.quantity,
                 "state": r.state, "reason": r.reason} for r in result.decision.criteria]
    return record, criteria


def _data_uri(html: str) -> str:
    return "data:text/html;charset=utf-8;base64," + base64.b64encode(html.encode("utf-8")).decode("ascii")


@functools.lru_cache(maxsize=len(DEMOS))
def _demo_result(name: str, project_root: Path) -> EvaluationResult:
    """Computed on the first request of each server instance, then reused (same files, same seed)."""
    return run_evaluation(project_root / DEMOS[name][0])


def create_app(data_dir=None, public_demo: bool = False, project_root=PROJECT_ROOT) -> FastAPI:
    """``public_demo``: stateless mode for a public deployment (see the module docstring).

    ``project_root``: folder holding ``examples/`` and ``experiments/``, to give when the
    package is installed outside the repository (e.g. by the hosting platform).
    """
    project_root = Path(project_root).resolve()
    example_dir = project_root / "examples" / "synthetic_demo"
    history = runs_dir = None
    if not public_demo:
        if data_dir is None:
            raise ValueError("data_dir is required outside the public demo mode")
        data_dir = Path(data_dir).resolve()
        runs_dir = data_dir / "runs"
        history = History(data_dir / "history.sqlite")
    app = FastAPI(title="MedVision QA", docs_url=None, redoc_url=None, openapi_url=None)
    common = dict(public=public_demo, github=GITHUB_URL)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", APP_CSP)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        lang = _language(request.query_params.get("lang"))
        if exc.status_code == 404:
            return not_found(lang)
        return _page("web_error.html.j2", lang, status_code=exc.status_code, path="/", **common)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return _page("web_error.html.j2", _language(request.query_params.get("lang")), status_code=500,
                     path="/", **common)

    def not_found(lang):
        return _page("web_not_found.html.j2", lang, status_code=404, path="/", **common)

    def index(lang, errors=(), status_code=200):
        max_bytes = PUBLIC_MAX_FILE_BYTES if public_demo else MAX_FILE_BYTES
        return _page("web_index.html.j2", lang, status_code=status_code, path="/", errors=list(errors),
                     history=[] if public_demo else history.recent(), load_messages=load_messages,
                     example_files=EXAMPLE_FILES, max_files=MAX_DATA_FILES, max_mb=max_bytes // (1024 * 1024),
                     max_resamples=PUBLIC_MAX_RESAMPLES, **common)

    def result_page(result, lang, path, actions, note=None):
        record, criteria = _summary(result)
        return _page("web_evaluation.html.j2", lang, path=path, record=record,
                     decision_reason=result.decision.reason, criteria=criteria, actions=actions,
                     note=note, **common)

    def evaluate_without_storing(lang, run_id, config, data_files):
        """Public demo: the files live in a temporary folder deleted before the response."""
        with tempfile.TemporaryDirectory(prefix="medvision-qa-") as tmp:
            workspace = Path(tmp) / run_id
            try:
                config_path = _save_uploads(workspace, config, data_files, PUBLIC_MAX_FILE_BYTES)
                if load_config(config_path).bootstrap_resamples > PUBLIC_MAX_RESAMPLES:
                    raise ConfigError(msg("web.public_resamples", max=PUBLIC_MAX_RESAMPLES))
                result = run_evaluation(config_path, run_id=run_id)
            except UploadRejected as exc:
                return index(lang, exc.errors, exc.status_code)
            except (ConfigError, ValidationError) as exc:
                # Rendered now to show the uploaded file names, not the server's temporary folder.
                folders = {f"{folder}{os.sep}" for folder in (workspace, workspace.resolve())}
                errors = []
                for error in [msg("web.rejected")] + _shown_errors(_rejection_errors(exc)):
                    text = error.render(lang)
                    for folder in folders:
                        text = text.replace(folder, "")
                    errors.append(text)
                return index(lang, errors, 422)
        actions = []
        for report_lang in LANGUAGES:
            suffix = "" if report_lang == DEFAULT_LANGUAGE else f".{report_lang}"
            actions.append({"label": t(f"web.download_report_{report_lang}", lang),
                            "href": _data_uri(render_report(result, report_lang)),
                            "download": f"VVR-{run_id}{suffix}.html"})
        return result_page(result, lang, "/", actions, note=msg("web.public_not_stored"))

    @app.get("/", response_class=HTMLResponse)
    def home(lang: str | None = None):
        return index(_language(lang))

    @app.post("/evaluations")
    def create_evaluation(lang: str | None = None, config: UploadFile = File(None),
                          data_files: list[UploadFile] = File([])):
        lang = _language(lang)
        run_id = str(uuid.uuid4())
        if public_demo:
            return evaluate_without_storing(lang, run_id, config, data_files)
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
            return index(lang, [msg("web.rejected")] + _shown_errors(errors), 422)
        finally:
            if not completed and workspace.exists():
                shutil.rmtree(workspace)  # keep no data from a rejected evaluation

    def completed_record(run_id: str):
        if public_demo or not RUN_ID_PATTERN.fullmatch(run_id):
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
            return not_found(lang)
        criteria = [dict(c, reason=load_message(c["reason"])) for c in json.loads(record.criteria_json)]
        base = f"/evaluations/{run_id}/report"
        suffix = "" if lang == DEFAULT_LANGUAGE else f"?lang={lang}"
        actions = [{"label": t("web.open_report", lang), "href": base + suffix},
                   {"label": t("web.download_report", lang), "href": f"{base}/download{suffix}"}]
        return _page("web_evaluation.html.j2", lang, path=f"/evaluations/{run_id}", record=record,
                     decision_reason=load_text(record.decision_reason), criteria=criteria, actions=actions,
                     note=None, **common)

    def report_file(run_id: str, lang: str) -> Path:
        path = runs_dir / run_id / REPORT_FILES[lang]
        return path if path.is_file() else runs_dir / run_id / REPORT_FILES[DEFAULT_LANGUAGE]

    @app.get("/evaluations/{run_id}/report")
    def view_report(run_id: str, lang: str | None = None):
        lang = _language(lang)
        if completed_record(run_id) is None:
            return not_found(lang)
        return FileResponse(report_file(run_id, lang), media_type="text/html; charset=utf-8",
                            headers={"Content-Security-Policy": REPORT_CSP})

    @app.get("/evaluations/{run_id}/report/download")
    def download_report(run_id: str, lang: str | None = None):
        lang = _language(lang)
        if completed_record(run_id) is None:
            return not_found(lang)
        suffix = "" if lang == DEFAULT_LANGUAGE else f".{lang}"
        return FileResponse(report_file(run_id, lang), media_type="text/html; charset=utf-8",
                            filename=f"VVR-{run_id}{suffix}.html", headers={"Content-Security-Policy": REPORT_CSP})

    @app.get("/demo/{name}", response_class=HTMLResponse)
    def show_demo(name: str, lang: str | None = None):
        lang = _language(lang)
        if name not in DEMOS:
            return not_found(lang)
        result = _demo_result(name, project_root)
        suffix = "" if lang == DEFAULT_LANGUAGE else f"?lang={lang}"
        actions = [{"label": t("web.open_report", lang), "href": f"/demo/{name}/report{suffix}"},
                   {"label": t("web.download_report", lang), "href": f"/demo/{name}/report/download{suffix}"}]
        return result_page(result, lang, f"/demo/{name}", actions, note=msg(DEMOS[name][1]))

    def demo_report(name: str, lang: str | None, download: bool):
        lang = _language(lang)
        if name not in DEMOS:
            return not_found(lang)
        headers = {"Content-Security-Policy": REPORT_CSP}
        if download:
            suffix = "" if lang == DEFAULT_LANGUAGE else f".{lang}"
            headers["Content-Disposition"] = f'attachment; filename="VVR-{name}{suffix}.html"'
        return HTMLResponse(render_report(_demo_result(name, project_root), lang), headers=headers)

    @app.get("/demo/{name}/report")
    def view_demo_report(name: str, lang: str | None = None):
        return demo_report(name, lang, download=False)

    @app.get("/demo/{name}/report/download")
    def download_demo_report(name: str, lang: str | None = None):
        return demo_report(name, lang, download=True)

    @app.get("/examples/{name}")
    def example_file(name: str):
        if name not in EXAMPLE_FILES or not (example_dir / name).is_file():
            return not_found(DEFAULT_LANGUAGE)
        media = "text/csv" if name.endswith(".csv") else "application/toml"
        return Response((example_dir / name).read_bytes(), media_type=f"{media}; charset=utf-8",
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
