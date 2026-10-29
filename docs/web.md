# Local web interface — v0.1

[日本語](ja/web.md)

Implementation: `src/medvision_qa/web.py`, `src/medvision_qa/history.py`, templates
`src/medvision_qa/templates/web_*.html.j2`. Tests: `tests/test_web.py`,
`tests/test_history.py`.

```bash
pip install -e ".[web]"
python -m medvision_qa.web                # http://127.0.0.1:8000 (Japanese: /?lang=ja)
python -m medvision_qa.web --port 8080 --data-dir D:/evaluations
```

## 1. Workflow

1. **Home** (`/`): upload form and history of evaluations. The link at the top right
   switches between English and Japanese (`?lang=ja`); the choice follows every page.
2. Upload a `.toml` configuration and the CSV files it references (4 at most). The CSV
   names must match the paths in the configuration. The files of the synthetic demo,
   including a Japanese configuration (`config.ja.toml`), can be downloaded from the home
   page.
3. **Run**: validation, calculations and decision (a few seconds), then redirect to the
   result page.
4. **Result** (`/evaluations/<id>`): overall decision and the state of each criterion with
   its justification. Links to open or download the Version Verification Record in the
   current language.
5. **Rejection** (invalid configuration or data): the list of errors is shown (50 at most,
   complete list in the history). No report is produced and the uploaded files are
   **deleted**.

## 2. Local storage

```
medvision_data/
├── history.sqlite          # one row per evaluation, completed or rejected
└── runs/<id>/              # completed evaluations only
    ├── config.toml, *.csv  # uploaded files, byte for byte
    ├── report.html         # English report
    └── report.ja.html      # Japanese report
```

The same identifier (UUID4) is used for the run, the folder, the history row and the
report. Since the files are kept unchanged, their SHA-256 in the report remain
verifiable. The history stores messages (decision reasons, errors) as message keys with
their parameters, so it can be shown in either language. The `medvision_data/` folder is
excluded from git.

## 3. Security (spec § 12)

| Measure | Detail |
|---|---|
| Local listening only | `127.0.0.1`, no option to listen on the network |
| No external call | no outgoing request, no JavaScript, no remote resource |
| File names | `^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$`, no folder; `.toml` / `.csv` extension; no duplicate |
| Size | 50 MB per file, 4 CSV files at most |
| Configuration paths | confined to the evaluation folder (`..` and absolute paths refused) |
| Identifiers in the URL | UUID4 checked by regular expression, then looked up in the history |
| Content | only CSV and TOML are read; nothing is executed or deserialised otherwise |
| Headers | CSP `default-src 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` |
| Escaping | all user text goes through Jinja2 escaping (tested with an HTML injection) |
| SQL | parameterised queries (tested) |
| API documentation | `/docs`, `/redoc`, `/openapi.json` disabled |
| Language parameter | only `en` and `ja` are accepted; any other value falls back to English |

## 4. Limits

- Single-user application, without authentication or CSRF protection: it must not be
  exposed on a network.
- Synchronous evaluation: the page waits for the calculations (about 6 s for the 872-case
  demo with 2,000 draws; both reports are generated).
- The configuration is uploaded as is. There is no form to compose the criteria: this is
  deliberate, since the versioned file is the record of the criteria defined in advance.
- No deletion of an evaluation from the interface (delete the folder and the row by hand).
