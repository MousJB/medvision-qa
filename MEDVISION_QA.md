# MedVision QA — Full project specification

[日本語](MEDVISION_QA.ja.md)

**Version:** 1.0
**Reference date:** 29 October 2026
**MVP target duration:** 30 days
**Status:** working specification; some technical choices remain to be validated.

---

## 1. Executive summary

**MedVision QA** is a tool for the verification, comparison and technical documentation of medical image classification model versions.

From predictions produced by two versions of a model, the application validates the data, computes relevant metrics, quantifies uncertainty, compares performance on the same cases, applies acceptance criteria defined in advance and generates a **Version Verification Record** in HTML format.

The goal is to make version evaluations more reproducible, more traceable and easier for a technical or quality team to review.

MedVision QA is a **technical evaluation aid**, not a medical device, a diagnostic tool, a clinical validation, a regulatory certification or proof of compliance.

### Value proposition

A simple, integrated workflow to:

1. check the quality of prediction files;
2. compute defined and documented metrics;
3. compare two versions evaluated on the same cases;
4. apply pre-established acceptance criteria;
5. keep the parameters and the limits of the analysis;
6. produce a self-contained, reproducible and understandable HTML report.

### Differentiation hypothesis

The differentiation to test is not "there is no competing tool". Experiment-tracking tools, medical imaging libraries and research platforms already exist. The hypothesis is that some users would value a compact workflow combining input validation, statistical comparison, explicit acceptance criteria and a versioned verification report.

This hypothesis must be validated with real users.

---

## 2. Context and problem

Teams that develop medical imaging models may need to compare a new version with a reference version, document the results and explain whether predefined technical criteria are met.

A single accuracy score is not always enough. A serious comparison may require:

- per-class metrics;
- a confusion matrix;
- confidence intervals;
- a paired comparison when both versions were evaluated on the same cases;
- a check of the input files and of the identity of the cases;
- acceptance criteria defined before the analysis;
- metadata that allow the analysis to be reproduced or audited;
- an explicit statement of what the results do not allow one to conclude.

The project aims to make these steps less scattered and to reduce processing errors and overreaching conclusions.

### Target users to explore

- Machine Learning engineers working on medical imaging;
- medical AI researchers;
- technical verification and validation teams;
- quality managers working with development teams;
- small teams that need a reproducible report without deploying a full platform.

These profiles are starting hypotheses, not validated market segments.

---

## 3. Objectives

### Technical objectives

- Build a working, testable Python tool.
- Strictly validate prediction files.
- Compute standard metrics with an explicit definition.
- Compare two versions on the same cases.
- Quantify uncertainty when the method applies.
- Apply predefined acceptance criteria without inventing them.
- Generate a self-contained HTML report with results, metadata and limits.
- Keep a record of the configurations and artefacts used.
- Demonstrate the workflow on a medical imaging example, if the data and usage rights allow it.

### Skills demonstrated

The project must demonstrate:

- Python and good development practice;
- data processing and validation;
- evaluation of classification models;
- applied statistics and uncertainty;
- understanding of the specifics of medical imaging;
- automated testing;
- reproducibility and traceability;
- the ability to explain the scientific limits of a result.

It must never be presented as a certified or clinically validated product.

---

## 4. Non-goals and scope limits

The MVP will not try to:

- diagnose a patient;
- make a clinical decision;
- certify a medical model;
- demonstrate clinical safety;
- certify compliance with ISO 13485, the FDA QMSR or any other regulation;
- replace a clinical validation, a quality system or a human review;
- guarantee the absence of bias, data leakage or regression;
- host medical data in a multi-tenant cloud service;
- provide multi-user authentication;
- execute arbitrary code supplied by users;
- automatically download datasets subject to restrictions;
- necessarily train a new model if the data, time or hardware do not allow it;
- include a large Next.js frontend in the MVP without an established user need.

The report is technical documentation of the analysis performed. On its own, it is not proof of regulatory compliance.

---

## 5. Expected behaviour

### Inputs

The user provides:

- a reference predictions file (version A);
- a predictions file of the new version (version B), for comparisons;
- the associated ground truth, if it is not already in the files;
- the definition of the classes and their order;
- the available metadata about the versions;
- the acceptance criteria defined before the analysis;
- protocol and sample-size justification information, when it exists.

### Workflow

1. The user creates an evaluation and fills in the metadata.
2. The application checks the schema and the consistency of the files.
3. Cases and labels are aligned using explicit identifiers.
4. The application refuses invalid inputs instead of silently removing rows.
5. Metrics are computed with their definitions and parameters.
6. Confidence intervals and statistical tests are computed only if their conditions of application are met.
7. Versions are compared on the same cases when the comparison is paired.
8. The results are checked against the pre-established acceptance criteria.
9. The application produces a conclusion among the allowed states and explains its reasoning.
10. A self-contained HTML report is generated with the results, metadata, limits and warnings.

### Outputs

- metric results;
- confusion matrices;
- confidence intervals, if they can be computed;
- statistical comparison results, if applicable;
- the state of each criterion;
- a justified overall decision;
- a log of validations and errors;
- a self-contained HTML report;
- the metadata needed to understand and reproduce the analysis.

---

## 6. Strict data validation

Input validation is a core feature, not an incidental step.

### Required checks

- required columns present;
- case identifiers not empty;
- no unauthorised duplicates;
- no missing values in required fields;
- labels in the list of allowed classes;
- predictions and ground truth consistent;
- scores and probabilities numeric, finite and within the expected bounds;
- sum of probabilities consistent with 1 within a documented tolerance, when multiclass probabilities are expected;
- explicit and consistent class order;
- no missing or extra cases in a paired comparison;
- consistent formats and types;
- identification of the rows or fields behind each error.

### Behaviour on error

- Never silently remove rows.
- Never replace an invalid value with a default value without explicit and traceable agreement.
- Block the affected calculations when the data do not meet the requirements.
- Show actionable error messages.
- Keep a summary of the checks run.

Case alignment rules must be explicit. Two files are not paired simply because they contain the same number of rows.

---

## 7. Metrics and statistical methods

Methods must be implemented with tests and explicit definitions. Metrics that do not apply must not be replaced by invented values.

### Classification metrics

Depending on the task and the available data:

- accuracy;
- per-class precision;
- per-class recall;
- per-class F1-score;
- macro-F1;
- confusion matrix;
- sensitivity and specificity when their definition is appropriate and the positive class is explicitly defined;
- AUROC when suitable continuous scores are available and the structure of the task allows it.

The report must state the positive class, the aggregation strategy, the class order and the definition of each metric.

When a metric cannot be computed (for example, a class absent from the ground truth), the application must use a documented state or report that the metric is undefined. It must not hide the problem.

### Confidence intervals

- Use a bootstrap suited to the data type and the metric.
- Record the number of resamples, the method, the seed and the resampling unit.
- Describe the assumptions and limits.
- Do not claim patient-level inference if patient identifiers or the grouping structure are not available.
- Do not mistake a wide confidence interval for proof of no difference.

### Comparing two versions

Versions must be evaluated on the same cases for paired comparisons.

- McNemar: only for a paired comparison of binary categorical outcomes, with the test conditions and variants documented.
- AUROC: paired DeLong when the conditions are met and the implementation is validated; otherwise, consider a properly designed paired bootstrap.
- Other metrics: use a method suited to the metric, the paired structure and the assumptions.
- Do not pick a statistical test only because it is easy to implement.
- Document the assumptions, the limits and the reasons why a method is or is not available.

#### Independent validation of DeLong

R and `pROC::roc.test` can serve as an independent validation reference, but R must not become a runtime dependency of the product.

If R is unavailable:

1. do not block the earlier phases;
2. look for reliable, independently verified reference results, with documented provenance;
3. if sufficient independent validation is not possible, do not claim that the DeLong implementation is validated;
4. use a properly tested alternative method, such as a paired bootstrap, or mark the comparison as unavailable.

Never invent reference results.

### Interpretation

- A non-significant result does not prove equivalence.
- A non-significant difference does not prove the absence of regression.
- An average improvement does not imply an improvement for every class or subgroup.
- A metric alone does not prove clinical utility.
- A conclusion must be limited to the protocol, data and methods actually used.

---

## 8. Acceptance criteria and decision engine

Criteria must be defined **before** the analysis. The application must not choose thresholds automatically after seeing the results.

### States per criterion

- `SATISFIED`: the elements required for the criterion are present and the predefined criterion is met.
- `NOT_SATISFIED`: the required elements are available and the predefined criterion is not met.
- `INCONCLUSIVE`: the available data, precision, assumptions or methods do not allow a decision.

The overall state must explain the rules for aggregating criteria. It must not hide an unmet or inconclusive criterion behind an overall average.

### Non-inferiority

A non-inferiority analysis requires in particular:

- a non-inferiority margin defined in advance;
- a defined metric and direction of effect;
- a suitable statistical method;
- a confidence interval and a decision rule consistent with the protocol.

Never conclude non-inferiority simply because no statistically significant difference was observed.

---

## 9. Sample size justification

The application must distinguish the number of cases actually evaluated from the justification of the sample size.

### Allowed states

1. **`Provided`**: the user provided a justification, a method, the assumptions, the parameters and, if applicable, a reference.
2. **`Not provided`**: no justification was provided. Show exactly: **"Not provided"**.
3. **`Not applicable`**: the user explicitly chose this state and gave a reason.
4. **`Based on data availability`**: the user states that the number of cases is dictated by data availability. Show a warning that this is not a statistical justification.

### Rules

- Do not create a justification automatically.
- Do not treat the number of available cases as a statistical justification.
- Do not derive a statistical power without explicit assumptions.
- Record the text provided, the selected state and the date.
- Show the actual sample size and the justification state separately.

---

## 10. HTML report: Version Verification Record

The report is the central deliverable of the project. It must be self-contained, readable and documented well enough for another person to understand what was run.

### Mandatory sections

1. Report and run identifier.
2. Date and time of the evaluation.
3. Objective and description of the comparison.
4. Identifiers of the compared versions.
5. Available information on the code, commit, weights and their hashes.
6. Dataset manifest and SHA-256 hash, when available.
7. File provenance and status of the information not provided.
8. Preprocessing, configuration, dependencies and seeds.
9. Class definition and class order.
10. Summary of data validations.
11. Metrics and definitions.
12. Confusion matrices.
13. Confidence intervals and parameters.
14. Statistical tests, assumptions and limits.
15. Acceptance criteria defined before the analysis.
16. State of each criterion and reasoned overall conclusion.
17. Sample size justification and its state.
18. Robustness test results, if any.
19. Items not available or not run.
20. Limitations of the analysis.
21. Mandatory section **"What This Report Cannot Establish"**.

### Minimum text for "What This Report Cannot Establish"

The report must state at least:

- A non-significant result does not prove the absence of regression, equivalence or non-inferiority.
- This analysis is not a clinical validation, nor a demonstration of clinical safety.
- This report does not certify compliance with ISO 13485, the FDA QMSR or any other regulation.
- Synthetic sensitivity tests do not validate real clinical acquisition conditions.
- Near-duplicate detection alone does not prove data leakage or patient identity.
- The conclusions are limited to the data, protocol, assumptions and methods actually used.

### Traceability and integrity

When the elements are available, record:

- the data manifest hash;
- artefact identifiers and hashes;
- code version and commit;
- dependency versions;
- configuration and seeds;
- parameters of the metrics and statistical methods;
- validation status;
- timestamp and run identifier.

Unavailable information must be explicitly marked as unavailable. Do not invent a commit, a hash, a model identifier or a provenance.

---

## 11. Technical architecture

### MVP stack

- **Python**: business logic, validation, metrics and statistics.
- **FastAPI**: routes and request handling.
- **Jinja2**: rendering of the HTML pages.
- **SQLite**: local history of evaluations and metadata.
- **NumPy / SciPy / scikit-learn**: numerical computing and metrics, as verified needs require.
- **pytest**: automated tests.
- **R + pROC**: optional tool for the independent validation of DeLong, not a runtime dependency.
- **Self-contained HTML**: report that can be exported and read without a heavy frontend.

### Why not use Next.js in the MVP?

A Next.js frontend would enlarge the development surface without a demonstrated user benefit at this stage. FastAPI and Jinja2 are enough for a first working interface. A more elaborate interface can be added if user feedback justifies it.

### Indicative layout

```text
medvision-qa/
├── app/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   │   ├── validation.py
│   │   ├── metrics.py
│   │   ├── confidence_intervals.py
│   │   ├── comparison.py
│   │   ├── decision_engine.py
│   │   └── report.py
│   ├── models/
│   ├── templates/
│   └── static/
├── tests/
│   ├── test_validation.py
│   ├── test_metrics.py
│   ├── test_confidence_intervals.py
│   ├── test_comparison.py
│   ├── test_decision_engine.py
│   └── test_report.py
├── examples/
├── docs/
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

This layout is indicative and can be adapted to real needs. Do not create empty modules or useless layers only to follow this tree.

---

## 12. Security, privacy and data handling

The MVP must favour local execution and limit data transfers.

### Requirements

- No external calls to LLMs or APIs to analyse the data.
- No execution of arbitrary code supplied by the user.
- No blind deserialisation of untrusted pickle files or models.
- Path validation and protection against directory traversal.
- Reasonable file size limits and error handling.
- No unnecessary personal data in reports or logs.
- No automatic download of restricted datasets.
- No promise of regulatory compliance or absolute security.

The README must explain the security assumptions, the data used in the demo and the limits of the local mode.

---

## 13. Medical imaging demonstration

### Candidate project

The existing brain tumour MRI classification repository can serve as a case study if the data, licence and artefacts are suitable:

`https://github.com/MousJB/brain-tumor-mri-classification`

Do not assume the dataset structure, splits or results are correct before inspection.

### Steps

1. Inspect the repository, the dataset, its licence and its provenance.
2. Check the training, validation and test partitions.
3. Detect exact duplicates with cryptographic hashes.
4. Detect near-duplicates with a suitable similarity method.
5. Manually inspect the flagged cases before any conclusion.
6. If resources and rights allow, train two real versions of the model.
7. Record the configurations, seeds, checkpoints and artefact identifiers.
8. Generate predictions of both versions on the same independent cases.
9. Use MedVision QA to compare the predictions and produce the report.
10. Document what was run, what was not, and why.

### If the real dataset is not ready

The image analysis phase must not block the MVP.

- Use clearly labelled fixtures or synthetic images to test the pipeline.
- If genuine prediction files are already available and usable, use them to demonstrate the comparison without retraining the models.
- Explain in the README why the real analysis or the retraining was not done.
- Never present synthetic data as real clinical data.

### Interpreting duplicates

- An identical hash signals identical content at file level.
- Perceptual similarity signals a resemblance to inspect.
- A near-duplicate does not prove the identity of a patient.
- The presence of a duplicate does not automatically prove data leakage.
- Any claim of leakage must rest on provenance, partitions and a documented inspection.

### Robustness tests

Synthetic tests can study the effect of Gaussian noise or reduced resolution on the predictions, if the image pipeline allows it.

They must be presented as synthetic sensitivity tests. They do not necessarily reproduce real clinical acquisition conditions and are not a clinical validation.

---

## 14. 30-day development plan

The schedule is a target, not an obligation to deliver unvalidated features. Each phase moves to the next only after its tests pass and its results are reviewed.

### Phase 0 — Scoping and inspection (days 1–3)

- Inspect the repository, the environment and the existing data.
- Confirm the prediction formats.
- Define the schemas and class conventions.
- Define the acceptance criteria and metadata.
- Check the licences and usage rights of the data.
- Create the repository skeleton, the tests and the initial README.

**Gate:** schema and scope documented; reproducible environment; basic tests runnable.

### Phase 1 — Validation, metrics and confidence intervals (days 4–9)

- Strict CSV validation.
- Explicit case alignment.
- Classification metrics.
- Confusion matrix.
- Bootstrap and suitable confidence intervals.
- Unit tests on normal, edge and error cases.
- Documentation of the metrics and undefined behaviours.

**Gate:** green tests; values checked on controlled examples; no silent removal of data; no undefined metric presented as valid.

### Phase 2 — Statistical comparison and decision (days 10–14)

- Comparison of two versions on the same cases.
- McNemar when the conditions are met.
- AUROC and a suitable comparison method if scores are available.
- Independent validation of DeLong if possible; otherwise, do not claim it is validated.
- Decision engine `SATISFIED`, `NOT_SATISFIED`, `INCONCLUSIVE`.
- Tests on limits, assumptions and inconclusive states.

**Gate:** methods correctly selected; pre-established criteria; green tests; justified and traceable conclusion.

### Phase 3 — HTML report (days 15–17)

- Generate the Version Verification Record.
- Include the available metadata and identify the missing ones.
- Include the sample size justification in its four states.
- Add "What This Report Cannot Establish".
- Test the generation and the readability of the report.
- Check that the report invents no data.

**Gate:** report reproducible, readable, consistent with the calculations and explicitly limited in its conclusions.

### Phase 4 — Image analysis and robustness, conditional (days 18–23)

- Inspect the real dataset if available and allowed.
- Detect exact duplicates and near-duplicates.
- Examine the flagged results.
- Run synthetic sensitivity tests.
- Train two real versions only if the data, licences, resources and time allow.
- Otherwise, use synthetic fixtures or genuine predictions already available, stating the limits clearly.

**Gate:** traceable and correctly labelled results; no unsupported claim about data leakage or performance.

**Important:** this phase is conditional. Its unavailability does not block the main MVP.

### Phase 5 — Interface and end-to-end workflow (days 24–27)

- FastAPI routes.
- Jinja2 forms and pages.
- File upload and validation.
- Launching an evaluation.
- Display of results and criteria.
- Local history with SQLite.
- Download of the HTML report.
- End-to-end tests.

**Gate:** a user can run the main workflow end to end without editing code by hand.

### Finalisation (days 28–30)

- Rerun every test.
- Fix blocking problems.
- Check the installation instructions.
- Prepare a reproducible demo.
- Add screenshots if they bring real value.
- Finalise the README and the known limits.
- Prepare a short portfolio presentation and a demo video, if useful.

---

## 15. Test strategy

### Unit tests

- expected metric values on simple cases;
- absent labels and imbalanced classes;
- missing and extra columns;
- duplicate identifiers;
- missing and non-finite values;
- out-of-bounds scores;
- inconsistent class order;
- unpaired cases;
- confidence intervals with reproducible seeds;
- satisfied, unsatisfied and inconclusive criteria;
- sample size justification states;
- complete report and missing metadata.

### Statistical tests

- comparison with independently computed results;
- cases where the assumptions of a test are not met;
- checks of the direction of effects;
- checks of the non-inferiority logic;
- tests showing that a non-significant result does not automatically produce a conclusion of equivalence.

### Integration tests

- CSV import;
- validation;
- metric computation;
- version comparison;
- criteria evaluation;
- SQLite storage;
- report generation and download.

### Minimum expected quality

- automated tests runnable locally;
- no silent errors;
- explicit and actionable errors;
- results reproducible within the limits of the methods used;
- documentation of assumptions and limits.

Do not announce "all tests pass" without actually running the suite in the environment concerned.

---

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Real dataset unavailable | Continue the MVP with controlled tests; make the image phase conditional |
| Uncertain licence or provenance | Do not use the data before clarification; document the rights |
| Excessive statistical complexity | Implement methods gradually; do not expose an unvalidated method |
| DeLong not verified | Do not claim validation; use a tested paired bootstrap or mark the option unavailable |
| Scope too wide | Keep the core CSV → metrics → comparison → decision → report |
| Overreaching scientific conclusion | Explicit states, visible limits, pre-established criteria |
| Sensitive data | Local execution, minimisation, no external calls |
| False signal of data leakage | Review duplicates and check provenance before any conclusion |

---

## 17. Success indicators

### Technical success of the MVP

- a valid file can be evaluated;
- an invalid file is rejected with explanations;
- metrics are tested on reference cases;
- two versions can be compared on paired cases;
- criteria are evaluated according to explicit rules;
- inconclusive states are correctly represented;
- the HTML report is generated and reproducible;
- limits and missing data are visible;
- installation and demo are documented.

### Portfolio success

- an outside person can understand the problem and run the demo;
- the tests can be run;
- the results shown are real and verifiable;
- the report sets out the assumptions and limits;
- the project allows a discussion of scientific and technical choices in an interview.

---

## 18. Development rules with Claude Code

The project must be developed **phase by phase**, not by asking the tool to generate the whole application at once.

### Working rules

1. First inspect the existing repository and environment.
2. Read the files and preserve the work already present.
3. State the exact scope of the current phase.
4. Implement only that phase.
5. Write the tests together with the code.
6. Run the tests and fix the failures.
7. Check critical calculations against independent examples.
8. Never invent results, data, hashes, references or validations.
9. Document unavailable methods and limits.
10. Summarise the files created/modified, the tests actually run, their results and the remaining problems.
11. Move to the next phase only when the current phase meets its gate.
12. If a prerequisite is missing, explain the blocker and propose an alternative that does not compromise scientific integrity.

### First instruction to Claude Code

> Start by inspecting the repository and the environment. Read the full specification `MEDVISION_QA.md`. Implement only Phase 1: strict CSV validation, explicit case alignment, classification metrics, confusion matrix, bootstrap confidence intervals where they apply, and automated tests. Do not yet implement the full interface, the advanced statistical comparison, the final report generation or the Phase 4 features. Do not remove any row silently, do not invent any data and do not replace invalid values with default values. Add tests for normal, edge and invalid cases. Run the test suite, fix the failures and finish with a factual summary of the files changed, the tests run, the results and the limits. Do not declare Phase 1 finished if the tests or checks are not conclusive.

---

## 19. Final decisions

- **Name:** MedVision QA.
- **Central deliverable:** Version Verification Record in HTML format.
- **Objective:** reproducible comparative evaluation and technical documentation of medical image classification model versions.
- **MVP stack:** Python, FastAPI, Jinja2, SQLite, NumPy/SciPy/scikit-learn, pytest.
- **Development:** by phases, with green tests as gates.
- **Frontend:** no Next.js in the MVP.
- **Real data:** wanted for a strong demonstration, but not required to unblock the technical core.
- **DeLong:** independent validation if possible; no claim of validation without proof.
- **Sample size:** explicit state, no invented justification.
- **Report:** limits and non-goals visible.
- **Regulation:** no claim of certification or compliance.
- **Languages (added after the MVP):** code and documentation in English; every generated output also available in Japanese. This specification was first written in French (see the git history).
- **Target duration:** 30 days, adjustable to results, data and constraints.

## Conclusion

MedVision QA must be a technical evaluation tool that is modest in its promises, solid in its calculations and transparent about its limits. Its portfolio value comes less from the number of features than from the quality of the validations, the statistical rigour, the reproducibility and the ability to produce a report that other people can review and understand.
