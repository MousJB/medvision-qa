# MedVision QA

[![tests](https://github.com/MousJB/medvision-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/MousJB/medvision-qa/actions/workflows/tests.yml)

[日本語](README.ja.md)

A tool for the comparative verification and technical documentation of medical image
classification model versions.

From the predictions of two model versions on the same cases, MedVision QA validates the
data, computes metrics with their uncertainty, applies acceptance criteria defined in
advance, and produces an HTML report: the *Version Verification Record*, in English or
Japanese.

> **MedVision QA is not a medical device**, a diagnostic tool, a clinical validation or
> proof of regulatory compliance (ISO 13485, FDA QMSR or other).

**Live demo: <https://medvision-qa.vercel.app>** (English and Japanese, no sign-in). It runs
the synthetic example and the real brain MRI evaluation on the server in one click, and
accepts your own files. Research prototype, not for clinical use: see
[Public demo](#public-demo).

## Engineering approach

Each design choice below is checked by code, tests or the git history.

| Choice | Why | Evidence |
|---|---|---|
| Invalid input is rejected, never cleaned | A silently dropped row changes the metrics without anyone knowing | Every violation is reported with file, line, column and rule: [validation.py](src/medvision_qa/validation.py), [tests/test_validation.py](tests/test_validation.py) |
| Cases are joined on `case_id`, never on row order | Two files in different orders would otherwise be compared case against wrong case | Missing or extra cases are errors: [alignment.py](src/medvision_qa/alignment.py), [tests/test_alignment.py](tests/test_alignment.py) |
| Criteria are written before the results | Choosing a threshold after seeing the results biases the conclusion | The MRI criteria were committed in `6de2a12`, before any training. The report records the SHA-256 of the configuration |
| Decisions use confidence-interval bounds only | A point estimate above a threshold is not evidence | The interval contains the threshold → INCONCLUSIVE, never SATISFIED. Non-inferiority needs a margin set in advance: [decision_engine.py](src/medvision_qa/decision_engine.py) |
| Resampling by patient when `patient_id` is given | Slices of one patient are not independent; a per-image bootstrap gives intervals that are too narrow | Interval more than 2× too narrow on a synthetic example: [tests/test_confidence_intervals.py](tests/test_confidence_intervals.py). McNemar is disabled when pairs are clustered |
| An undefined metric stays undefined | Replacing 0/0 with 0 makes a model look worse or better than it is | Each undefined value carries its reason: [docs/metrics.md](docs/metrics.md) |
| Results are checked against independent code | A tool that checks models must itself be checked | Metrics against scikit-learn, McNemar against a hand-written exact test. The MRI results were recomputed separately: [docs/audit.md](docs/audit.md) |
| What is not validated is not offered | An unvalidated test presented as reliable is worse than none | DeLong is not implemented (no independent reference). The AUROC difference uses the paired bootstrap |
| Every report is traceable and reproducible | A result that cannot be traced cannot be audited | SHA-256 of the data, configuration and weights, plus commit, package versions and run ID. Regenerating a report changes only its run ID and date |
| Limits are part of the output | A report that only shows numbers invites over-reading | Every report ends with "What This Report Cannot Establish". The open points are listed in [docs/audit.md](docs/audit.md#4-what-remains-unverified) |

The automated tests run on every push (Linux and Windows, Python 3.11 and 3.12):
[.github/workflows/tests.yml](.github/workflows/tests.yml).

## Result on real MRI data

Two versions trained on the public figshare dataset (CC BY 4.0), patient-disjoint test set
(64 patients), criteria fixed before training: **INCONCLUSIVE**. ResNet18 is not inferior
to SimpleCNN and has a better AUROC, but its glioma sensitivity (0.929, CI [0.865; 0.970])
does not demonstrate the 0.90 threshold. The data audit also found duplicated patient
identifiers in figshare, and **16.5% of the test images copied into the training set** of
the Kaggle MRI-BT dataset. Details:
[experiments/brain_mri/README.md](experiments/brain_mri/README.md). Reports:
[English](experiments/brain_mri/figshare_eval/report.html),
[Japanese](experiments/brain_mri/figshare_eval/report.ja.html).

## Demo (synthetic data)

Web interface (file upload, result, history, report download; English or Japanese):

```bash
python -m medvision_qa.web        # then open http://127.0.0.1:8000 (Japanese: /?lang=ja)
```

The demo files can be downloaded from the home page. On the command line:

```bash
python -m medvision_qa examples/synthetic_demo/config.toml -o reports/demo.html
python -m medvision_qa examples/synthetic_demo/config.ja.toml -o reports/demo.ja.html --lang ja
```

The CSV files in [examples/synthetic_demo/](examples/synthetic_demo/) are **synthetic**:
872 simulated images for 450 patients. They can be regenerated byte for byte with
`python examples/synthetic_demo/generate.py`. The report says so in a banner.

### Public demo

<https://medvision-qa.vercel.app> serves the same web interface in a public, stateless mode
(`create_app(public_demo=True)` in [app.py](app.py)):

- `/demo/synthetic` and `/demo/brain-mri` run the evaluation on the server from the files
  committed in this repository (about 10 s on the first request of a server instance). The
  brain MRI report computed online is identical to
  [the committed one](experiments/brain_mri/figshare_eval/report.html) except for the run
  identifier, the date and the Python patch version.
- Uploads are evaluated in a temporary folder deleted before the response is sent. There is
  no history and nothing is stored: both reports are returned inside the result page.
- Limits on this deployment: 4 MB per request (platform limit), at most 2,000 bootstrap
  resamples, 60 s per request. The web pages contain no JavaScript. The Version
  Verification Record is a wide document: on a phone, its larger tables scroll horizontally.

Deployment: Vercel Python runtime, one function. [vercel.json](vercel.json) sets the
duration limit; [uv.lock](uv.lock) pins the same versions as
[requirements-lock.txt](requirements-lock.txt); [.vercelignore](.vercelignore) uploads only
the files the demo needs (never `data/`, weights or local environments). No environment
variable or secret is needed. To redeploy from a clone linked to the Vercel project:
`vercel deploy --prod`.

## Usage

From a TOML configuration ([example](docs/evaluation_config.md#1-complete-example)):

```bash
python -m medvision_qa config.toml -o report.html [--lang ja]
```

Or from Python:

```python
from medvision_qa.evaluation import run_evaluation
from medvision_qa.report import write_report

result = run_evaluation("config.toml")
print(result.decision.state, "-", result.decision.reason)        # English
print(result.decision.reason.render("ja"))                        # Japanese
for c in result.decision.criteria:
    print(c.criterion.id, c.state, c.reason)
write_report(result, "report.ja.html", lang="ja")
```

Invalid input raises `ValidationError`, whose `.issues` lists every violation (file, line,
column, value, rule). An invalid configuration raises `ConfigError`.

### Example input and output

Input: one ground truth file and one predictions file per version, joined on `case_id`
(never on row order). Full rules: [docs/data_format.md](docs/data_format.md).

```text
ground_truth.csv                     preds_v2.csv
case_id,true_label,patient_id        case_id,predicted_label,score_glioma,score_meningioma,score_notumor,score_pituitary
img_00000,meningioma,P0000           img_00000,pituitary,0.077062,0.382078,0.050313,0.490547
img_00001,glioma,P0001               img_00001,notumor,0.253126,0.177946,0.346870,0.222058
```

Output on valid data: the decision on the console, and the HTML report.

```text
$ python -m medvision_qa examples/synthetic_demo/config.toml -o reports/demo.html
SATISFIED — all 3 criteria are satisfied
Report: reports/demo.html
```

Output on invalid data (here a duplicated `case_id` and a score of 1.2): exit code 2, no report.

```text
Invalid data, no report produced.
2 validation issue(s):
  - [unique_case_id] preds_v2.csv, line 4, column 'case_id': case_id already present on line 2 (value: 'img_00000')
  - [score_in_bounds] preds_v2.csv, line 3, column 'score_glioma': score outside [0, 1] (value: '1.2')
```

The reports are self-contained HTML files (no script, no external resource). GitHub shows
their source code: download them and open them in a browser to read them.

## Architecture

```text
config.toml ─► config.py            strict TOML reading: classes, versions, statistics, criteria
CSV files   ─► validation.py        every violation collected, no row dropped or corrected
               alignment.py         join on case_id; missing or extra cases are errors
               metrics.py           confusion matrix, per-class and binary metrics, AUROC
               confidence_intervals.py   percentile bootstrap, by patient when patient_id is given
               comparison.py        paired bootstrap of B − A, exact McNemar (when applicable)
               decision_engine.py   SATISFIED / NOT_SATISFIED / INCONCLUSIVE from CI bounds only
               evaluation.py        runs the steps above, records run id, date, package versions
               report.py + templates/   Version Verification Record (HTML, English or Japanese)
               web.py + history.py  FastAPI interface: local (SQLite history) or public demo (stateless)
app.py      ─► entry point of the public demo on Vercel
               duplicates.py        exact (SHA-256) and near (pHash) duplicate detection
```

Core dependencies: numpy, scipy, Jinja2, and scikit-learn (not used by the metric code:
the tests use it as an independent reference, and the report records its version). The web
interface adds FastAPI, uvicorn and python-multipart.

## Documentation

- [MEDVISION_QA.md](MEDVISION_QA.md): full specification
- [docs/data_format.md](docs/data_format.md): input CSV format and validation rules
- [docs/metrics.md](docs/metrics.md): metric definitions, undefined cases, bootstrap, limits
- [docs/evaluation_config.md](docs/evaluation_config.md): configuration, acceptance criteria, decision rules
- [docs/comparison.md](docs/comparison.md): paired A/B comparison, McNemar, DeLong status, traceability
- [docs/report.md](docs/report.md): content of the Version Verification Record, guaranteed properties, languages
- [docs/web.md](docs/web.md): web interface, local storage, security measures
- [docs/phase0_inspection.md](docs/phase0_inspection.md): inspection of the environment, the MRI repository and the dataset
- [docs/phase4_data_sources.md](docs/phase4_data_sources.md): data sources and licences
- [docs/audit.md](docs/audit.md): audit of 2026-10-29: commands run, independent checks, findings, what remains unverified, demo script

Every document has a Japanese version in [docs/ja/](docs/ja/).

## Installation (development)

Python ≥ 3.11. Tested by CI on Ubuntu and Windows (Python 3.12, locked dependencies) and
on Ubuntu with Python 3.11 (latest dependencies); developed on Windows 10, Python 3.12.6.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"      # library + web interface + test tools
pytest
```

`pip install -e .` alone installs the core (validation, statistics, report, command line)
without FastAPI. The `[web]` extra adds the interface.

To reproduce the tested environment exactly: `pip install -r requirements-lock.txt`, then
`pip install -e . --no-deps`.

## Data and security

- No network call, no call to an LLM or to an external API to analyse the data. The local
  web interface listens on `127.0.0.1` only and must not be exposed on a network (no
  authentication, shared history). Only the public demo mode is meant to be exposed: it
  stores nothing and keeps no history, and it asks users not to upload patient data.
- No dataset is included or downloaded automatically. The `.gitignore` excludes `data/`,
  medical images and model weights.
- No pickle files or models are loaded: the tool only reads CSV files and a TOML
  configuration.
- The tests use synthetic data, always identified as such.

## Languages

The code, messages and documentation are in English. Every generated output (HTML report,
web interface, validation and configuration errors) also exists in Japanese, from a single
message catalog ([src/medvision_qa/i18n.py](src/medvision_qa/i18n.py)). The project was
first written in French; the git history before the translation commit keeps the French
originals.
