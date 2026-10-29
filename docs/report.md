# HTML report: Version Verification Record — v0.1

[日本語](ja/report.md)

Implementation: `src/medvision_qa/report.py`, template
`src/medvision_qa/templates/report.html.j2`, messages in `src/medvision_qa/i18n.py`.
Tests: `tests/test_report.py`, `tests/test_i18n.py`.

```bash
python -m medvision_qa config.toml -o report.html               # English
python -m medvision_qa config.toml -o report.ja.html --lang ja  # Japanese
```

Exit code: `0` if the report is generated, whatever the decision; `2` if the
configuration or the data are invalid. In that case no report is produced and the
errors are printed.

## 1. Guaranteed properties (tested)

| Property | How |
|---|---|
| The 21 sections of the specification (§ 10), in order | `<h2 id="s1">` to `<h2 id="s21">` |
| Minimum text of "What This Report Cannot Establish" | constant `CANNOT_ESTABLISH`, shown in full |
| No invented data | everything comes from `EvaluationResult`; an empty field is shown as "Not provided" in place **and** summarised in section 19 |
| Numbers consistent with the calculations | CIs, justifications, confusion matrices and hashes compared with the computed objects |
| Self-contained | inline CSS, no script, no external URL, no remote font |
| User text escaped | titles, descriptions and justifications go through Jinja2 HTML escaping |
| No absolute path | files are shown relative to the configuration (no user name or local tree) |
| Reproducible | same configuration → identical report, except for the run identifier and timestamp; LF line endings on every OS |
| 4 sample-size states | `Provided`, `Not provided`, `Not applicable`, `Based on data availability` (+ warning); the actual size is always shown separately |
| Two languages | English (default) and Japanese render the same content: same sections, same numbers, same table cells (tested) |

## 2. Content by section

| § | Section | Source |
|---|---|---|
| 1 | Identifiers | run UUID (also identifies the report), SHA-256 of the configuration |
| 2 | Date and time | start of the run, UTC |
| 3 | Objective | `evaluation.title`, `evaluation.objective`, comparison type, number of cases |
| 4 | Versions | `versions.*.id`, description, whether scores are present |
| 5 | Code and weights | **declared** `code_commit`, `weights_sha256` (the weights are not read) |
| 6 | Dataset | `data.description`, `data.nature`, `data.manifest_sha256` |
| 7 | Provenance | relative path, **computed** SHA-256 and row count of each CSV |
| 8 | Preprocessing, dependencies | `versions.*.preprocessing`, seed, tolerance, Python, package versions |
| 9 | Classes | indexed order, derived binary task |
| 10 | Validation | ground truth mode, alignment, checks run per file |
| 11 | Metrics | estimate and CI per version, reasons for undefined values, warnings, definitions |
| 12 | Confusion matrices | one per version |
| 13 | CI parameters | method, level, draws, seed, unit and number of units |
| 14 | Statistical tests | paired Δ = B − A, McNemar (or the reason it does not apply), DeLong status |
| 15 | Criteria | definition of each criterion, configuration hash |
| 16 | Decision | state and justification per criterion, overall conclusion, aggregation rule |
| 17 | Sample size | actual size, state, text provided, warning if applicable |
| 18 | Robustness | "not run" (not supported in v0.1) |
| 19 | Not available | generated list: missing metadata, undefined metrics, tests that do not apply |
| 20 | Limitations | list generated from the data (nature, `patient_id`, multiplicity...) and general limits |
| 21 | What This Report Cannot Establish | fixed text of the specification |

## 3. Languages

Every label and every generated sentence (justifications, undefined-value reasons,
limitations) comes from the message catalog `src/medvision_qa/i18n.py`, where each entry
holds its English and Japanese text. The engine stores messages as key + parameters, so
one evaluation can be rendered in either language. `tests/test_i18n.py` checks that both
languages use the same placeholders and that every key used in the code exists.

The free text of the configuration (title, objective, descriptions) is shown as written.
For a report entirely in Japanese, write it in Japanese (see
`examples/synthetic_demo/config.ja.toml`).

## 4. Known limits

- No charts (ROC curves, etc.): tables only.
- Declared metadata (commit, weight hash, preprocessing) are shown as is: the tool cannot
  check that they match the models actually used.
