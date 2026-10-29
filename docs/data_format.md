# Input file format — v0.1

[日本語](ja/data_format.md)

Status: defined in Phase 0, **implemented in Phase 1** (`src/medvision_qa/validation.py`,
`src/medvision_qa/alignment.py`), tested in `tests/test_validation.py` and
`tests/test_alignment.py`. Files are read with the standard `csv` module (not pandas),
to avoid any implicit conversion.

"Line" means the physical line of the file (1 = header). It can differ from the record
number when a quoted field contains a line break.

General principle: **every violation is a blocking error.** No row is removed and no
value is corrected, normalised or replaced silently.

---

## 1. Rules common to every CSV

| Rule | Behaviour |
|---|---|
| Encoding | UTF-8, with or without BOM (Excel adds a BOM). Any other encoding → error. |
| Separator | Comma `,`. Quoting per RFC 4180. |
| Header | Required, first line. |
| Duplicate column names | Error. |
| Unknown columns | Error, unless they start with `meta_` (kept, never used in calculations). |
| Empty line or wrong number of fields | Error with line number. |
| Leading/trailing spaces in a value | Error (no silent `strip()`). |
| File without data rows | Error. |

Each error gives: file, line number (1 = header), column, offending value, and the rule
violated.

---

## 2. Classes

Classes are declared in the evaluation configuration
([evaluation_config.md](evaluation_config.md)), **not inferred from the data**.

- Ordered list, at least 2 classes, no duplicate.
- Names: `^[A-Za-z0-9_-]+$`, case-sensitive (`Glioma` ≠ `glioma`).
- The declared order fixes the row/column order of the confusion matrix and the expected
  order of the score columns.
- A declared class may be absent from the data: this is not a format error, but the
  metrics that depend on it are marked **undefined** (Phase 1).

Example for the MRI dataset: `["glioma", "meningioma", "notumor", "pituitary"]`.

### Positive classes (derived binary task)

`positive` is a non-empty list of declared classes, different from the full set of
classes. It defines a binary "positives vs the rest" task:

- binary truth: `true_label ∈ positive`;
- binary prediction: `predicted_label ∈ positive` (existing multiclass decision, no new
  threshold);
- binary score: sum of the `score_<class>` of the positive classes (used for AUROC only).

MRI example, tumour vs no tumour: `positive = ["glioma", "meningioma", "pituitary"]`.
One-vs-rest: `positive = ["glioma"]`.

---

## 3. Ground truth file (`ground_truth.csv`)

Single source of the reference labels, shared by versions A and B.

| Column | Required | Type | Rules |
|---|---|---|---|
| `case_id` | yes | text | not empty, unique in the file |
| `true_label` | yes | text | must be one of the declared classes |
| `patient_id` | no | text | not empty if the column exists; several cases may share a patient |
| `meta_*` | no | text | ignored by calculations |

Without `patient_id`, every inference is **at image/case level**, and the report says so.
With `patient_id`, resampling is done by patient (cluster bootstrap).

```csv
case_id,true_label,patient_id
img_0001,glioma,P001
img_0002,notumor,P002
```

---

## 4. Predictions file (one per version)

| Column | Required | Type | Rules |
|---|---|---|---|
| `case_id` | yes | text | not empty, unique in the file |
| `predicted_label` | yes | text | must be one of the declared classes |
| `score_<class>` | no, but **all or nothing** | real | one column per declared class, none extra |
| `true_label` | no | text | see § 5 |
| `meta_*` | no | text | ignored by calculations |

### Rules on scores

If at least one `score_*` column is present:

1. there must be exactly one per declared class (none missing, none extra);
2. each value is a finite real in `[0, 1]` (`nan`, `inf`, empty → error);
3. each row sums to 1 within a tolerance (default `1e-3`, configurable and reported in
   the report), so the scores must be softmax-like outputs;
4. `predicted_label` must be one of the classes with the highest score (argmax; on a tie,
   any of the tied classes is accepted). An inconsistency is an error. v0.1 does not
   support threshold-based decision rules.

Without scores, score-based metrics (AUROC) are **unavailable**, not estimated.

```csv
case_id,predicted_label,score_glioma,score_meningioma,score_notumor,score_pituitary
img_0001,glioma,0.91,0.05,0.02,0.02
img_0002,notumor,0.03,0.10,0.80,0.07
```

---

## 5. Where the ground truth lives

Two modes, mutually exclusive and explicit in the configuration:

- **`separate_file` mode (recommended)**: one `ground_truth.csv`. If a predictions file
  also contains `true_label`, every value must equal the one in the ground truth file,
  otherwise error.
- **`embedded` mode**: no separate file; every predictions file contains `true_label`.
  In an A/B comparison, `true_label` must be identical in A and B for each `case_id`,
  otherwise error. `patient_id` is not available in this mode.

---

## 6. Case alignment

- Alignment is done **only on `case_id`**, by exact string equality. Row order does not
  matter.
- Two files are never paired by position or by row count.
- The sets of `case_id` in the ground truth, A and B must be **identical**. Any missing or
  extra case → error, with the list of identifiers concerned.
- There is no "intersection" mode that would drop the cases not shared. If a subset is
  needed, it must be selected upstream and documented.

---

## 7. Known limits of the v0.1 format

- Single-label classification only (no multi-label, no segmentation).
- No single-column binary scores: for a binary task, provide both columns.
- The format cannot check that the `case_id` values really refer to the same images for
  A and B; it only checks that the identifiers are consistent. The data manifest hash
  (`data.manifest_sha256`) is there to trace this.
