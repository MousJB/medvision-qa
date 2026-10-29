# Technical and scientific audit — 2026-10-29

[日本語](ja/audit.md)

Scope: the whole repository at commit `ea6a4cf` (software, CSV validation, metrics,
bootstrap, paired comparison, decision engine, HTML report, web interface, MRI
experiment). Everything below was run on Windows 10, Python 3.12.6. Nothing here is a
clinical validation or a regulatory assessment.

## 1. Commands run and results

| Check | Command | Result |
|---|---|---|
| Test suite, before the fixes | `.venv\Scripts\python -m pytest` | 870 passed, 0 failed, 0 skipped |
| Clean install from the lock file | new venv, `pip install -r requirements-lock.txt`, `pip install -e . --no-deps`, `pip check`, `pytest` | no broken requirement; 870 passed |
| Lint (not configured in the project) | `ruff check --isolated --select E9,F src tests experiments examples` (ruff 0.17.3) | no error |
| Real MRI reports reproduced | `python -m medvision_qa experiments/brain_mri/figshare_eval/config.toml -o …` (EN and JA), then `diff` | only the run identifier and the run date differ |
| Synthetic demo regenerated | `python examples/synthetic_demo/generate.py` into another folder, `cmp` | the three CSV files are byte-identical |
| Web interface, real server | `python -m medvision_qa.web`, driven with `curl` | upload → 303 → result page; report downloaded (EN, JA); invalid upload → 422 with the reason; `..` paths → 404/400; no file kept for a rejected run |
| Downloaded report | `grep` on the file | no `<script>`, no external resource; "What This Report Cannot Establish" section present |
| Secrets and data in git | `git log --all -p` searched for keys, tokens, passwords; list of every file ever committed | none; no image, weight file or database ever committed |
| Test suite, after the fixes | `.venv\Scripts\python -m pytest` | 875 passed, 0 failed, 0 skipped |
| Continuous integration (added by this audit) | [tests.yml](../.github/workflows/tests.yml): Ubuntu and Windows with the lock file (Python 3.12), Ubuntu with the latest dependencies (Python 3.11) | first run: 1 failure on both Ubuntu jobs (finding below); after the fix, 875 passed on all three |

## 2. Independent verifications

- **figshare results** (scikit-learn, plus a cluster bootstrap written separately, with
  another seed). Point estimates identical to the report: accuracy 0.8003 / 0.9278,
  macro-F1 0.7946 / 0.9232, glioma sensitivity of B 0.9288, AUROC 0.9160 / 0.9904.
  95% intervals within 0.002 of the report's: glioma sensitivity of B [0.863; 0.971]
  (report [0.865; 0.970]), Δ macro-F1 [0.076; 0.189] ([0.074; 0.188]), Δ AUROC
  [0.029; 0.136] ([0.031; 0.135]). Same decisions: C1 SATISFIED, C2 INCONCLUSIVE, C3
  SATISFIED. The gap is Monte-Carlo error, not a different method.
- **MRI-BT exact duplicates** (byte SHA-256 recomputed from the cached Kaggle files): 300
  groups, 695 pairs, 365 Training ↔ Testing pairs, 216 / 1,311 Testing images with a copy
  in Training (meningioma 106, no-tumor 105, pituitary 5), 0 group with conflicting labels.
  These are the values given in the experiment README.
- **Pre-registration**: `git diff 6de2a12 HEAD -- figshare_eval/config.toml` changes only
  comments, free text and the metadata filled in after training (commits, weight hashes,
  manifest hash). Classes, statistics, sample size and criteria are unchanged.
- **figshare licence**: `data/figshare/article.json` (downloaded figshare metadata) gives
  CC BY 4.0, version 8, DOI 10.6084/m9.figshare.1512427.v8.
- Metrics against scikit-learn and McNemar against a hand-written exact test were
  already in the test suite (`tests/test_metrics.py`, `tests/test_comparison.py`).

## 3. Findings

No P0 finding. Every finding below is fixed, except those marked "not fixed".

| Priority | Finding | Evidence | Action |
|---|---|---|---|
| P1 | The headline figure "216 / 1,311 (16.5%)" and the counts "695 pairs" and "365 Training ↔ Testing pairs" were not in any versioned output. `summary.json` counted the pairs of a group from its first file only (263 Training ↔ Testing). | `audit_mri_bt.py`, former line 87; `mri_bt_audit/summary.json` | The script now writes every pair, the Testing images with a copy in Training and the label conflicts. Script re-run: the new fields match the independent count; the other fields and `flagged_pairs.csv` are unchanged. |
| P2 | The audit script crashed at its last line on a Windows console (cp1252 cannot encode "↔"), after writing its files. Two console messages were still in French. | log of the re-run | ASCII console output; messages in English. |
| P2 | A missing configuration file gave a Python traceback (exit code 1) instead of an error message. | `python -m medvision_qa missing.toml -o x.html` | `ConfigError` "Unreadable configuration", exit code 2; two regression tests. |
| P2 | The report said a high p-value proves nothing, but not that a low p-value does not measure practical or clinical importance. | `r.mcnemar_note` in `i18n.py` | Sentence added (EN, JA), in the report and in `docs/comparison.md`; test added; MRI reports regenerated (numbers unchanged). |
| P2 | The README had no architecture overview and no input/output example; GitHub shows the HTML reports as source code. | `README.md` | Sections added (EN, JA), with real outputs of the tool. |
| P2 | The README gave "Python ≥ 3.11" while only Python 3.12.6 was tested. | `docs/phase0_inspection.md` | Tested versions stated; now checked by CI. |
| P2 | On Linux, `C:/gt.csv` in a configuration was not seen as an absolute path. It was still rejected, but as "file not found". Found by the first CI run. | `config.py`, `_data_path` | Paths absolute under the POSIX or the Windows convention are rejected as absolute on every OS; two test cases added. |
| P3 | scikit-learn is a runtime dependency but is only used by the tests (and its version is recorded in the report). | `grep sklearn src/` | Not fixed: changing it would change the report's traceability fields, for no user benefit. |
| P2 | No continuous integration: nothing showed publicly that the tests pass, and Linux and Python 3.11 were never tested. | no `.github/` | GitHub Actions workflow added (see § 1). |
| P3 | No lint configuration. | no `ruff`/`flake8` config | Not fixed: outside the MVP. The lint above was run by hand. |

## 4. What remains unverified

- **Training** was not re-run (GPU, partial CUDA determinism): the weight hashes and
  predictions are taken as committed. The evaluation from these predictions is reproduced.
- **Patient unit in figshare**: merging PIDs that share a root is an assumption, backed by
  a non-expert visual inspection. It was not checked against any clinical record.
- **Near-duplicates**: 26 of the 50 MRI-BT pairs with different labels were never
  inspected. Near-duplicates remain candidates, not evidence.
- **Licence of the Kaggle MRI-BT assembly** (including Br35H): not open; only file names
  and aggregates are versioned, which was checked.
- **DeLong** is not implemented and is not claimed: the AUROC difference uses the paired
  bootstrap.
- **Multiplicity**: criteria are evaluated without correction; the report says so. The
  overall SATISFIED requires every criterion to be satisfied.
- **Pre-registration** can only be checked through the git history (commit `6de2a12`);
  the tool cannot prove it.
- The report was checked through HTTP and its content, not visually in every browser.
- macOS was not tested.

## 5. Demonstration (3 to 5 minutes)

1. `python -m medvision_qa.web`, open http://127.0.0.1:8000. One sentence: "comparing two
   model versions on the same cases, with uncertainty and criteria fixed in advance".
2. Download the five demo files from the home page and upload them: validation passes,
   decision SATISFIED (synthetic data, stated in the banner).
3. Upload the configuration with only two CSV files: the evaluation is rejected, with the
   reason, and no file is kept.
4. Open the report: metrics with their CI, paired B − A differences, criteria.
5. Open `experiments/brain_mri/figshare_eval/report.html` (real data): C2 is INCONCLUSIVE
   because the CI of glioma sensitivity [0.865; 0.970] contains the 0.90 threshold, even
   though the estimate (0.929) is above it.
6. In that report: traceability (config hash, data hashes, weight hashes, commit), sample
   size "Based on data availability" with its warning, "What This Report Cannot Establish".
7. Say what is real (figshare evaluation, MRI-BT duplicates), what is synthetic (demo), and
   what is unverified (section 4).
