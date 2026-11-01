"""User-facing messages in English and Japanese.

Every message the tool shows (validation issues, configuration errors, undefined-metric
reasons, decision justifications, report and web interface labels) lives in ``MESSAGES``,
one entry per key with its English and Japanese text. Results keep a ``Text`` (key +
parameters) rather than a rendered string, so one evaluation can be rendered in either
language. ``str(text)`` renders English.
"""

from dataclasses import dataclass

LANGUAGES = ("en", "ja")
DEFAULT_LANGUAGE = "en"

# key: (English, Japanese). Both texts must use the same {placeholders}.
MESSAGES = {
    "raw": ("{text}", "{text}"),
    "sep": ("; ", "、"),

    # Decision states
    "state.SATISFIED": ("SATISFIED", "SATISFIED（基準充足）"),
    "state.NOT_SATISFIED": ("NOT_SATISFIED", "NOT_SATISFIED（基準不充足）"),
    "state.INCONCLUSIVE": ("INCONCLUSIVE", "INCONCLUSIVE（判定保留）"),

    # Validation issues (CSV files)
    "issue.line": ("line {line}", "{line} 行目"),
    "issue.column": ("column {column}", "列 {column}"),
    "issue.value": (" (value: {value})", "（値: {value}）"),
    "issue.more": ("... and {n} more issue(s).", "…ほか {n} 件の問題があります。"),
    "val.not_utf8": ("the file is not UTF-8 (byte {offset})",
                     "ファイルが UTF-8 ではありません（{offset} バイト目）"),
    "val.csv_malformed": ("malformed CSV: {error}", "CSV の形式が不正です: {error}"),
    "val.header_missing": ("header missing", "ヘッダー行がありません"),
    "val.column_whitespace": ("leading or trailing space in column name",
                              "列名の先頭または末尾に空白があります"),
    "val.duplicate_column": ("duplicate column", "列が重複しています"),
    "val.required_column_missing": ("required column missing", "必須の列がありません"),
    "val.unknown_column": ("unknown column; prefix it with {prefix} to keep it without using it",
                           "不明な列です。使用せずに残す場合は、列名の先頭に {prefix} を付けてください"),
    "val.no_data_rows": ("no data rows", "データ行がありません"),
    "val.empty_line": ("empty line", "空行があります"),
    "val.field_count": ("{found} field(s) instead of {expected}",
                        "フィールド数が {found} 個です（{expected} 個必要です）"),
    "val.value_whitespace": ("leading or trailing space in value", "値の先頭または末尾に空白があります"),
    "val.value_missing": ("missing value", "値がありません"),
    "val.duplicate_case_id": ("case_id already present on line {line}",
                              "case_id が {line} 行目と重複しています"),
    "val.label_undeclared": ("undeclared label (classes: {classes}; case-sensitive)",
                             "宣言されていないラベルです（クラス: {classes}。大文字と小文字は区別されます）"),
    "val.unexpected_score_column": ("unexpected score column in the ground truth",
                                    "正解データにスコア列を含めることはできません"),
    "val.score_not_numeric": ("non-numeric score (decimal format expected)",
                              "スコアが数値ではありません（10 進数の形式で記載してください）"),
    "val.score_not_finite": ("non-finite score", "スコアが有限の値ではありません"),
    "val.score_out_of_bounds": ("score outside [0, 1]", "スコアが [0, 1] の範囲外です"),
    "val.score_column_undeclared": ("score column for an undeclared class",
                                    "宣言されていないクラスのスコア列です"),
    "val.score_column_missing": ("score column missing (scores are all or nothing)",
                                 "スコア列が不足しています（スコアは全クラス分そろえるか、まったく含めないかのどちらかです）"),
    "val.score_sum": ("sum of scores = {total}, deviation from 1 > tolerance {tolerance}",
                      "スコアの合計が {total} で、1 との差が許容誤差 {tolerance} を超えています"),
    "val.not_argmax": ("predicted_label is not the class with the highest score ({argmax})",
                       "predicted_label が最大スコアのクラス（{argmax}）と一致しません"),
    "val.case_missing_here": ("case present in {reference} but missing here",
                              "{reference} にある症例が、このファイルにありません"),
    "val.case_extra": ("case absent from {reference}", "{reference} にない症例です"),
    "val.true_label_mismatch": ("true_label differs from the one in {reference} ({expected})",
                                "true_label が {reference} の値（{expected}）と異なります"),
    "val.true_label_required": ("embedded mode: a true_label column is required when there is no "
                                "ground truth file",
                                "embedded モードで正解データファイルがない場合は、true_label 列が必要です"),

    # Configuration errors
    "cfg.order_not_list": ("`order` must be a list of classes, not a string.",
                           "`order` は文字列ではなく、クラスのリストで指定してください。"),
    "cfg.positive_is_string": ('`positive` must be a list of classes, not a string: write ["{value}"].',
                               '`positive` は文字列ではなく、クラスのリストで指定してください（例: ["{value}"]）。'),
    "cfg.too_few_classes": ("At least 2 classes must be declared.", "クラスを 2 つ以上宣言してください。"),
    "cfg.class_name_invalid": ("Invalid class name: {name} (allowed characters: letters, digits, _ and -).",
                               "クラス名が不正です: {name}（使用できる文字は英字、数字、_、- のみです）。"),
    "cfg.class_duplicates": ("Classes declared more than once: {names}.",
                             "複数回宣言されたクラスがあります: {names}。"),
    "cfg.positive_undeclared": ("Undeclared positive classes: {names}.",
                                "陽性クラスに、宣言されていないクラスがあります: {names}。"),
    "cfg.positive_duplicate": ("Positive class declared more than once.",
                               "陽性クラスが重複して宣言されています。"),
    "cfg.positive_all": ("The positive classes cannot be all the classes: the binary task would have "
                         "no negative class.",
                         "すべてのクラスを陽性クラスにすることはできません。二値タスクに陰性クラスがなくなります。"),
    "cfg.resamples_invalid": ("bootstrap_resamples must be an integer ≥ {min}.",
                              "bootstrap_resamples は {min} 以上の整数で指定してください。"),
    "cfg.confidence_level_invalid": ("confidence_level must be a number strictly between 0 and 1.",
                                     "confidence_level は 0 より大きく 1 より小さい数値で指定してください。"),
    "cfg.seed_invalid": ("seed must be an integer ≥ 0 (required for reproducibility).",
                         "seed は 0 以上の整数で指定してください（再現性のため必須です）。"),
    "cfg.section_missing": ("Section [{where}] is missing.", "[{where}] セクションがありません。"),
    "cfg.not_a_table": ("[{where}] must be a table.", "[{where}] はテーブルで指定してください。"),
    "cfg.unknown_keys": ("Unknown key(s) in [{where}]: {keys}.", "[{where}] に不明なキーがあります: {keys}。"),
    "cfg.missing_keys": ("Required key(s) missing in [{where}]: {keys}.",
                         "[{where}] に必須キーがありません: {keys}。"),
    "cfg.not_a_string": ("{where} must be a string.", "{where} は文字列で指定してください。"),
    "cfg.value_whitespace": ("{where}: leading or trailing space in value.",
                             "{where}: 値の先頭または末尾に空白があります。"),
    "cfg.empty": ("{where} must not be empty.", "{where} を空にすることはできません。"),
    "cfg.pattern": ("{where}: {description} expected (or empty if not provided), got {value}.",
                    "{where}: {description}を指定してください（未提供の場合は空にします）。指定値: {value}"),
    "cfg.desc_commit": ("a hexadecimal commit hash (7 to 40 lowercase characters)",
                        "16 進数のコミットハッシュ（小文字 7〜40 文字）"),
    "cfg.desc_sha256": ("a lowercase hexadecimal SHA-256", "小文字 16 進数の SHA-256"),
    "cfg.not_a_number": ("{where} must be a finite number.", "{where} は有限の数値で指定してください。"),
    "cfg.absolute_path": ("{where}: absolute path refused; give a path relative to the configuration folder.",
                          "{where}: 絶対パスは使用できません。設定ファイルのフォルダーからの相対パスを指定してください。"),
    "cfg.path_escapes": ("{where}: the path leaves the configuration folder ({value}).",
                         "{where}: パスが設定ファイルのフォルダーの外を指しています（{value}）。"),
    "cfg.file_not_found": ("{where}: file not found ({value}).", "{where}: ファイルが見つかりません（{value}）。"),
    "cfg.one_of": ("{where} must be one of {values}.", "{where} には {values} のいずれかを指定してください。"),
    "cfg.not_a_list": ("{where} must be a list.", "{where} はリストで指定してください。"),
    "cfg.positive_not_list": ('classes.positive must be a list, e.g. ["glioma"].',
                              'classes.positive はリストで指定してください（例: ["glioma"]）。'),
    "cfg.unknown_versions": ("Unknown versions: {names} (only A and B are supported).",
                             "不明なバージョンがあります: {names}（指定できるのは A と B のみです）。"),
    "cfg.version_a_missing": ("[versions.A] is missing: the reference version is required.",
                              "[versions.A] がありません。基準バージョンは必須です。"),
    "cfg.same_version_ids": ("versions.A.id and versions.B.id must differ.",
                             "versions.A.id と versions.B.id には異なる値を指定してください。"),
    "cfg.tolerance_positive": ("statistics.probability_sum_tolerance must be > 0.",
                               "statistics.probability_sum_tolerance は 0 より大きい値で指定してください。"),
    "cfg.justification_required": ("sample_size.justification is required for status {status}.",
                                   "status が {status} の場合、sample_size.justification は必須です。"),
    "cfg.justification_must_be_empty": ("sample_size.justification must be empty for status 'not_provided'.",
                                        "status が 'not_provided' の場合、sample_size.justification は空にしてください。"),
    "cfg.no_criteria": ("No [[criteria]]: an evaluation without criteria produces no decision.",
                        "[[criteria]] がありません。基準のない評価では判定を出せません。"),
    "cfg.criteria_not_tables": ("[[criteria]] must be a list of tables.",
                                "[[criteria]] はテーブルのリストで指定してください。"),
    "cfg.duplicate_criterion": ("Duplicate criterion id: {id}.", "基準の id が重複しています: {id}。"),
    "cfg.class_required": ("{where}: metric {metric} requires `class` among {classes}.",
                           "{where}: 指標 {metric} では、`class` に {classes} のいずれかを指定する必要があります。"),
    "cfg.class_meaningless": ("{where}: `class` does not apply to metric {metric}.",
                              "{where}: 指標 {metric} には `class` を指定できません。"),
    "cfg.positive_required": ("{where}: metric {metric} requires classes.positive.",
                              "{where}: 指標 {metric} には classes.positive の指定が必要です。"),
    "cfg.threshold_range": ("{where}.threshold must be in [0, 1].",
                            "{where}.threshold は [0, 1] の範囲で指定してください。"),
    "cfg.version_undeclared": ("{where}.version: version {version} is not declared.",
                               "{where}.version: バージョン {version} は宣言されていません。"),
    "cfg.b_required": ("{where}: a {kind} criterion requires [versions.B].",
                       "{where}: {kind} の基準には [versions.B] が必要です。"),
    "cfg.margin_range": ("{where}.margin must be strictly between 0 and 1.",
                         "{where}.margin は 0 より大きく 1 より小さい値で指定してください。"),
    "cfg.unreadable": ("Unreadable configuration ({name}): {error}",
                       "設定ファイルを読み込めません（{name}）: {error}"),
    "cfg.schema_version": ("schema_version {found} is not supported (expected: {expected}).",
                           "schema_version {found} には対応していません（対応しているのは {expected} です）。"),
    "cfg.gt_mode": ("data.ground_truth_mode must be {a} or {b}.",
                    "data.ground_truth_mode には {a} または {b} を指定してください。"),
    "cfg.gt_file_must_be_empty": ("data.ground_truth_file must be empty in 'embedded' mode.",
                                  "'embedded' モードでは data.ground_truth_file を空にしてください。"),

    # Undefined metrics
    "metric.single_binary_class": ("only one binary class present (positives and negatives required)",
                                   "二値クラスの一方しか存在しません（陽性と陰性の両方が必要です）"),
    "metric.never_predicted": ("class {cls} never predicted", "クラス {cls} が一度も予測されていません"),
    "metric.absent_from_truth": ("class {cls} absent from the ground truth",
                                 "クラス {cls} が正解ラベルに存在しません"),
    "metric.absent_everywhere": ("class {cls} absent from both ground truth and predictions",
                                 "クラス {cls} が正解ラベルにも予測にも存在しません"),
    "metric.f1_undefined": ("F1 undefined for {classes}", "{classes} の F1 が未定義です"),
    "metric.no_positive_class": ("no positive class declared", "陽性クラスが宣言されていません"),
    "metric.no_positive_case": ("no positive case in the ground truth", "正解ラベルに陽性症例がありません"),
    "metric.no_negative_case": ("no negative case in the ground truth", "正解ラベルに陰性症例がありません"),
    "metric.no_scores": ("scores not provided", "スコアが提供されていません"),

    # Metric definitions
    "def.accuracy": ("Proportion of cases where predicted_label = true_label.",
                     "predicted_label が true_label と一致した症例の割合。"),
    "def.precision": ("TP / (TP + FP) for the class, one-vs-rest. Undefined if the class is never predicted.",
                      "クラスごとの TP / (TP + FP)（一対他）。そのクラスが一度も予測されない場合は未定義。"),
    "def.recall": ("TP / (TP + FN) for the class, one-vs-rest. Undefined if the class is absent from the "
                   "ground truth.",
                   "クラスごとの TP / (TP + FN)（一対他）。そのクラスが正解ラベルに存在しない場合は未定義。"),
    "def.f1": ("2·TP / (2·TP + FP + FN) for the class. Undefined if the class is absent from both the "
               "ground truth and the predictions.",
               "クラスごとの 2·TP / (2·TP + FP + FN)。そのクラスが正解ラベルにも予測にも存在しない場合は未定義。"),
    "def.macro_f1": ("Unweighted mean of the per-class F1 over all declared classes. Undefined if any F1 "
                     "is undefined.",
                     "宣言された全クラスの F1 の単純平均（重み付けなし）。いずれかの F1 が未定義なら未定義。"),
    "def.sensitivity": ("Derived binary task: TP / (TP + FN). Undefined without a declared positive class "
                        "or without a positive case.",
                        "派生二値タスクの TP / (TP + FN)。陽性クラスが宣言されていない場合、または陽性症例がない場合は未定義。"),
    "def.specificity": ("Derived binary task: TN / (TN + FP). Undefined without a declared positive class "
                        "or without a negative case.",
                        "派生二値タスクの TN / (TN + FP)。陽性クラスが宣言されていない場合、または陰性症例がない場合は未定義。"),
    "def.auroc": ("Derived binary task, positive score = sum of the positive classes' scores; "
                  "Mann-Whitney statistic, ties counted as 1/2. Undefined without scores, without a "
                  "declared positive class, or if only one of the two binary classes is present.",
                  "派生二値タスク。陽性スコアは陽性クラスのスコアの合計。Mann-Whitney 統計量で計算し、"
                  "同順位は 1/2 として数える。スコアがない場合、陽性クラスが宣言されていない場合、"
                  "または二値クラスの一方しか存在しない場合は未定義。"),

    # Confidence intervals
    "ci.zero_width_warning": ("zero-width interval: the percentile bootstrap underestimates uncertainty "
                              "when the metric is constant (e.g. at its bound 0 or 1)",
                              "幅ゼロの区間: 指標が一定の場合（例: 0 または 1 に張り付いている場合）、"
                              "パーセンタイル・ブートストラップは不確実性を過小評価します"),
    "ci.metric_undefined": ("metric undefined: {reason}", "指標が未定義: {reason}"),
    "ci.undefined_in_resamples": ("metric undefined in {count}/{total} resamples; discarding them would "
                                  "bias the interval",
                                  "{total} 回中 {count} 回のリサンプリングで指標が未定義です。"
                                  "これらを除外すると区間に偏りが生じます"),
    "ci.small_sample": ("{n} resampling unit(s) (< {min}): percentile bootstrap coverage not guaranteed",
                        "リサンプリング単位が {n} 個（{min} 未満）: パーセンタイル・ブートストラップの被覆確率は保証されません"),

    # Paired comparison
    "cmp.delong_status": ("not implemented: no independent reference (R/pROC) available to validate "
                          "it; the AUROC difference is estimated by paired bootstrap",
                          "未実装。検証に使える独立した参照実装（R/pROC）がないため。"
                          "AUROC の差は対応のあるブートストラップで推定している"),
    "cmp.mcnemar_method": ("Exact conditional McNemar (two-sided binomial on discordant pairs)",
                           "正確条件付きマクネマー検定（不一致ペアに対する両側二項検定）"),
    "cmp.undefined_for": ("metric undefined for {details}", "指標が未定義: {details}"),
    "cmp.undefined_detail": ("{version}: {reason}", "{version}（{reason}）"),
    "cmp.mcnemar_clustered": ("several cases per patient: the pairs are not independent, so the "
                              "McNemar test assumption does not hold",
                              "患者あたり複数の症例があるためペアが独立ではなく、マクネマー検定の前提を満たさない"),
    "cmp.mcnemar_no_discordant": ("no discordant pair: the test carries no information",
                                  "不一致ペアがないため、検定から得られる情報がない"),

    # Decision engine
    "dec.aggregation_rule": ("NOT_SATISFIED if at least one criterion is NOT_SATISFIED; otherwise "
                             "INCONCLUSIVE if at least one criterion is INCONCLUSIVE; SATISFIED only if "
                             "every criterion is SATISFIED.",
                             "NOT_SATISFIED の基準が 1 つでもあれば NOT_SATISFIED。そうでなく、"
                             "INCONCLUSIVE の基準が 1 つでもあれば INCONCLUSIVE。"
                             "すべての基準が SATISFIED の場合に限り SATISFIED。"),
    "dec.interval_undefined": ("interval cannot be computed: {reason}", "区間を計算できない: {reason}"),
    "dec.zero_width": ("zero-width interval: uncertainty cannot be estimated by the percentile "
                       "bootstrap on these data",
                       "幅ゼロの区間: このデータではパーセンタイル・ブートストラップで不確実性を推定できない"),
    "dec.ci": ("CI [{lower}, {upper}]", "信頼区間 [{lower}, {upper}]"),
    "dec.abs_satisfied": ("{ci}: lower bound ≥ threshold {t}", "{ci}: 下限が閾値 {t} 以上"),
    "dec.abs_not": ("{ci}: upper bound < threshold {t}", "{ci}: 上限が閾値 {t} 未満"),
    "dec.abs_inconclusive": ("{ci} contains the threshold {t}", "{ci} が閾値 {t} を含む"),
    "dec.ni_satisfied": ("{ci}: lower bound > −margin ({m})", "{ci}: 下限が −マージン（{m}）を上回る"),
    "dec.ni_not": ("{ci}: upper bound < −margin ({m}); B is inferior",
                   "{ci}: 上限が −マージン（{m}）を下回る。B は劣っている"),
    "dec.ni_inconclusive": ("{ci} contains −margin ({m}); non-inferiority is neither shown nor ruled out",
                            "{ci} が −マージン（{m}）を含む。非劣性は示されておらず、否定もされていない"),
    "dec.sup_satisfied": ("{ci}: lower bound > 0", "{ci}: 下限が 0 を上回る"),
    "dec.sup_not": ("{ci}: upper bound ≤ 0", "{ci}: 上限が 0 以下"),
    "dec.sup_inconclusive": ("{ci} contains 0; superiority is not shown", "{ci} が 0 を含む。優越性は示されていない"),
    "dec.not_satisfied": ("criterion(s) not satisfied: {ids}", "満たされなかった基準: {ids}"),
    "dec.inconclusive": ("inconclusive criterion(s): {ids}", "判定保留の基準: {ids}"),
    "dec.satisfied": ("all {n} criteria are satisfied", "{n} 件の基準をすべて満たしている"),

    # Report: header and navigation
    "r.html_title": ("Version Verification Record", "Version Verification Record（バージョン検証記録）"),
    "r.run": ("Run", "実行 ID"),
    "r.synthetic_title": ("Synthetic data.", "合成データ。"),
    "r.synthetic_banner": ("This report covers artificially generated data, not clinical data.",
                           "本レポートは人工的に生成したデータを対象としており、臨床データではない。"),
    "r.disclaimer": ("Technical evaluation document. It is not a clinical validation, a certification or "
                     "proof of regulatory compliance. See section 21.",
                     "技術評価のための文書である。臨床的妥当性確認、認証、規制適合の証明のいずれでもない。第 21 節を参照。"),
    "r.overall": ("Overall decision:", "総合判定:"),
    "r.aggregation_rule": ("Aggregation rule:", "集約規則:"),
    "r.s1": ("Report and run identifiers", "レポートおよび実行の識別子"),
    "r.s2": ("Evaluation date and time", "評価日時"),
    "r.s3": ("Objective and description of the comparison", "目的と比較の概要"),
    "r.s4": ("Identifiers of the compared versions", "比較対象バージョンの識別子"),
    "r.s5": ("Code, commits, weights and hashes", "コード、コミット、重み、ハッシュ"),
    "r.s6": ("Dataset manifest", "データセットのマニフェスト"),
    "r.s7": ("File provenance", "ファイルの来歴"),
    "r.s8": ("Preprocessing, configuration, dependencies and seeds", "前処理、設定、依存パッケージ、乱数シード"),
    "r.s9": ("Classes and class order", "クラスとクラスの順序"),
    "r.s10": ("Data validation summary", "データ検証の概要"),
    "r.s11": ("Metrics and definitions", "指標と定義"),
    "r.s12": ("Confusion matrices", "混同行列"),
    "r.s13": ("Confidence intervals and parameters", "信頼区間とパラメーター"),
    "r.s14": ("Statistical tests, assumptions and limits", "統計的検定、前提、限界"),
    "r.s15": ("Acceptance criteria defined before the analysis", "分析前に定めた受入基準"),
    "r.s16": ("State of each criterion and overall decision", "各基準の状態と総合判定"),
    "r.s17": ("Sample size justification", "サンプルサイズの根拠"),
    "r.s18": ("Robustness test results", "頑健性試験の結果"),
    "r.s19": ("Items not available or not run", "利用できない項目・実施していない項目"),
    "r.s20": ("Limitations of the analysis", "分析の限界"),
    "r.s21": ("What This Report Cannot Establish",
              "What This Report Cannot Establish（本レポートで立証できないこと）"),

    # Report: body
    "r.run_id": ("Run identifier", "実行 ID"),
    "r.run_id_note": ("(also identifies this report)", "（本レポートの識別子を兼ねる）"),
    "r.configuration": ("Configuration", "設定ファイル"),
    "r.started_utc": ("(UTC, start of the run)", "（UTC、実行開始時刻）"),
    "r.title": ("Title", "タイトル"),
    "r.objective": ("Objective", "目的"),
    "r.type": ("Type", "種別"),
    "r.paired_type": ("Paired comparison: B (candidate) against A (reference), on the same {n} cases",
                      "対応のある比較: 同一の {n} 症例で B（候補）を A（基準）と比較"),
    "r.single_type": ("Evaluation of a single version ({n} cases)", "単一バージョンの評価（{n} 症例）"),
    "r.role": ("Role", "役割"),
    "r.identifier": ("Identifier", "識別子"),
    "r.description": ("Description", "説明"),
    "r.scores_provided": ("Scores provided", "スコアの有無"),
    "r.reference": ("reference", "基準"),
    "r.candidate": ("candidate", "候補"),
    "r.yes": ("yes", "あり"),
    "r.no": ("no", "なし"),
    "r.version": ("Version", "バージョン"),
    "r.version_n": ("Version {v}", "バージョン {v}"),
    "r.code_commit": ("Code commit", "コードのコミット"),
    "r.weights_sha256": ("Weights SHA-256", "重みの SHA-256"),
    "r.declared_note": ("Values declared in the configuration, not checked by the tool (weights are not read).",
                        "設定ファイルで申告された値であり、本ツールでは検証していない（重みファイルは読み込まない）。"),
    "r.data_nature": ("Nature of the data", "データの種類"),
    "r.manifest_sha256": ("Manifest SHA-256", "マニフェストの SHA-256"),
    "r.nature.synthetic": ("Synthetic data", "合成データ"),
    "r.nature.clinical": ("Real clinical data (declared by the user)", "実臨床データ（利用者による申告）"),
    "r.file_relative": ("File (relative to the configuration)", "ファイル（設定ファイルからの相対パス）"),
    "r.sha256_computed": ("SHA-256 (computed)", "SHA-256（計算値）"),
    "r.rows": ("Rows", "行数"),
    "r.not_provided_note": ("Items not provided are summarised in section 19.", "未提供の項目は第 19 節にまとめている。"),
    "r.ground_truth": ("Ground truth", "正解データ"),
    "r.predictions_of": ("Predictions, version {v}", "予測（バージョン {v}）"),
    "r.declared_preprocessing": ("Declared preprocessing", "申告された前処理"),
    "r.seed": ("Seed", "乱数シード"),
    "r.tolerance": ("Score sum tolerance", "スコア合計の許容誤差"),
    "r.dependencies": ("Dependencies", "依存パッケージ"),
    "r.declared_order": ("Declared order", "宣言された順序"),
    "r.binary_task": ("Derived binary task", "派生二値タスク"),
    "r.binary_definition": ("positive = {positive}; negative = {negative}", "陽性 = {positive}、陰性 = {negative}"),
    "r.no_binary_task": ("none (no positive class declared)", "なし（陽性クラスの宣言なし）"),
    "r.ground_truth_mode": ("Ground truth mode:", "正解データのモード:"),
    "r.alignment": ("Strict alignment on case_id: {n} cases, identical in every file. No row was removed, "
                    "corrected or replaced.",
                    "case_id による厳密な照合: {n} 症例、すべてのファイルで一致。行の削除・修正・置換は一切行っていない。"),
    "r.file": ("File", "ファイル"),
    "r.checks_run": ("Checks run (all passed)", "実施したチェック（すべて合格）"),
    "r.metric": ("Metric", "指標"),
    "r.estimate": ("Estimate", "推定値"),
    "r.ci_level": ("{level}% CI", "{level}% 信頼区間"),
    "r.remarks": ("Remarks", "備考"),
    "r.definitions": ("Definitions", "定義"),
    "r.confusion_note": ("Rows = ground truth, columns = prediction.", "行 = 正解、列 = 予測。"),
    "r.method": ("Method", "手法"),
    "r.method_value": ("{method} bootstrap, two-sided, {quantiles} quantiles",
                       "{method} ブートストラップ（両側、分位点の計算法: {quantiles}）"),
    "r.level": ("Level", "信頼水準"),
    "r.resamples": ("Resamples", "リサンプリング回数"),
    "r.unit": ("Resampling unit", "リサンプリング単位"),
    "r.unit_value": ("{unit} ({n} units)", "{unit}（{n} 単位）"),
    "method.percentile": ("percentile", "パーセンタイル"),
    "quantiles.linear": ("linear", "線形補間"),
    "unit.patient": ("patient", "患者"),
    "unit.case": ("case", "症例"),
    "r.ci_note": ("An interval is produced only if the metric is defined on the full sample and in every "
                  "resample.",
                  "区間は、指標が全標本およびすべてのリサンプルで定義される場合にのみ算出する。"),
    "r.paired_differences": ("Paired differences Δ = B − A (paired bootstrap, same draws for A and B)",
                             "対応のある差 Δ = B − A（対応のあるブートストラップ。A と B に同じ抽出を使用）"),
    "r.ci": ("CI", "信頼区間"),
    "r.mcnemar_title": ("McNemar (informative, not used in decisions)", "マクネマー検定（参考値。判定には使用しない）"),
    "r.pairs": ("Pairs", "ペア"),
    "r.pairs_value": ("both correct: {both} · only A correct: {a} · only B correct: {b} · both wrong: {none}",
                      "両方正解: {both} · A のみ正解: {a} · B のみ正解: {b} · 両方不正解: {none}"),
    "r.p_value": ("p-value", "p 値"),
    "r.not_applicable": ("not applicable", "適用不可"),
    "r.mcnemar_note": ("Assumption: independent pairs. A high p-value proves neither equivalence nor the "
                       "absence of regression, and a low p-value does not measure the practical or clinical "
                       "importance of the difference.",
                       "前提: ペアが互いに独立であること。p 値が大きくても、同等性や性能低下がないことの証明にはならず、"
                       "p 値が小さくても、差の実用上・臨床上の重要性を示すものではない。"),
    "r.delong": ("DeLong", "DeLong 法"),
    "r.tests_not_run": ("Not run: a single version is declared.", "未実施: 宣言されたバージョンが 1 つのみ。"),
    "r.id": ("Id", "ID"),
    "r.kind": ("Type", "種別"),
    "r.quantity": ("Quantity", "評価対象"),
    "r.parameter": ("Parameter", "パラメーター"),
    "r.threshold": ("threshold {t}", "閾値 {t}"),
    "r.margin": ("margin {m}", "マージン {m}"),
    "r.criteria_note": ("The tool cannot prove the criteria were fixed before the analysis: compare the "
                        "configuration hash with its version history (e.g. git). Configuration SHA-256:",
                        "本ツールでは、基準が分析前に定められたことを証明できない。設定ファイルのハッシュを"
                        "バージョン履歴（git など）と照合すること。設定ファイルの SHA-256:"),
    "r.state": ("State", "状態"),
    "r.justification": ("Justification", "根拠"),
    "r.inconclusive_note": ("A criterion is INCONCLUSIVE if the interval is undefined or has zero width.",
                            "区間が未定義または幅ゼロの場合、その基準は INCONCLUSIVE とする。"),
    "r.actual_size": ("Actual size", "実際のサンプルサイズ"),
    "r.cases_n": ("{n} cases", "{n} 症例"),
    "r.cases_and_patients": ("{cases} cases, {patients} patients", "{cases} 症例、{patients} 患者"),
    "r.provided_text": ("Text provided", "記載内容"),
    "r.sample.provided": ("Provided", "記載あり"),
    "r.sample.not_provided": ("Not provided", "未提供"),
    "r.sample.not_applicable": ("Not applicable", "該当なし"),
    "r.sample.based_on_data_availability": ("Based on data availability", "データの入手可能性に基づく"),
    "r.availability_warning": ("A sample size dictated by data availability is not a statistical justification.",
                               "データの入手可能性で決まったサンプルサイズは、統計的な根拠にはならない。"),
    "r.robustness_not_run": ("Not run: this version of the tool does not include robustness tests.",
                             "未実施: 本バージョンのツールには頑健性試験の機能がない。"),
    "r.not_provided": ("Not provided", "未提供"),
    "r.footer": ("Generated by MedVision QA {version}. Self-contained report: no external resource, no script.",
                 "MedVision QA {version} により生成。外部リソースおよびスクリプトを含まない自己完結型のレポート。"),

    # Report: items not available
    "na.objective": ("Evaluation objective (evaluation.objective): Not provided",
                     "評価の目的（evaluation.objective）: 未提供"),
    "na.data_description": ("Data description (data.description): Not provided",
                            "データの説明（data.description）: 未提供"),
    "na.data_nature": ("Nature of the data (data.nature): Not provided", "データの種類（data.nature）: 未提供"),
    "na.manifest": ("SHA-256 hash of the data manifest (data.manifest_sha256): Not provided",
                    "データマニフェストの SHA-256（data.manifest_sha256）: 未提供"),
    "na.version_field": ("Version {v} — {label} (versions.{v}.{field}): Not provided",
                         "バージョン {v} — {label}（versions.{v}.{field}）: 未提供"),
    "field.code_commit": ("code commit", "コードのコミット"),
    "field.weights_sha256": ("weights hash", "重みのハッシュ"),
    "field.preprocessing": ("preprocessing", "前処理"),
    "field.description": ("description", "説明"),
    "na.sample_size": ("Sample size justification: Not provided", "サンプルサイズの根拠: 未提供"),
    "na.patient_ids": ("Patient identifiers (patient_id): not provided; no resampling by patient",
                       "患者 ID（patient_id）: 未提供。患者単位のリサンプリングは行っていない"),
    "na.metric_undefined": ("Version {v} — {key}: undefined ({reason})", "バージョン {v} — {key}: 未定義（{reason}）"),
    "na.ci_undefined": ("Version {v} — CI of {key}: cannot be computed ({reason})",
                        "バージョン {v} — {key} の信頼区間: 計算不可（{reason}）"),
    "na.mcnemar": ("McNemar test: not applicable ({reason})", "マクネマー検定: 適用不可（{reason}）"),
    "na.delong": ("DeLong test: {status}", "DeLong 法: {status}"),
    "na.no_comparison": ("Comparison between versions: not run (a single version declared)",
                         "バージョン間の比較: 未実施（宣言されたバージョンが 1 つのみ）"),
    "na.robustness": ("Robustness tests: not run (not supported by this version of the tool)",
                      "頑健性試験: 未実施（本バージョンのツールでは未対応）"),

    # Report: limitations
    "lim.synthetic": ("The data are synthetic: these results say nothing about performance on real data.",
                      "データは合成データである。これらの結果は、実データでの性能について何も示さない。"),
    "lim.nature_unknown": ("The nature of the data (synthetic or real) is not declared.",
                           "データの種類（合成データか実データか）が申告されていない。"),
    "lim.no_patient_id": ("Without a patient identifier, cases are assumed independent. If several images "
                          "come from the same patient, the confidence intervals are too narrow.",
                          "患者 ID がないため、各症例を独立とみなしている。同一患者の画像が複数含まれる場合、"
                          "信頼区間は実際より狭くなる。"),
    "lim.percentile": ("Percentile bootstrap: actual coverage may fall below the nominal level for small "
                       "samples and for metrics close to 0 or 1.",
                       "パーセンタイル・ブートストラップ: 標本が小さい場合や指標が 0 または 1 に近い場合、"
                       "実際の被覆確率が名目水準を下回ることがある。"),
    "lim.warnings": ("Some intervals carry warnings (see section 11).", "一部の区間には警告が付いている（第 11 節を参照）。"),
    "lim.multiplicity": ("{n} criteria evaluated without multiplicity correction.",
                         "{n} 件の基準を、多重性の調整なしで評価している。"),
    "lim.preregistration": ("The tool cannot prove the criteria were defined before the analysis; the "
                            "configuration hash lets you check this against an external history (git).",
                            "本ツールでは、基準が分析前に定められたことを証明できない。設定ファイルのハッシュを"
                            "外部の履歴（git）と照合すれば確認できる。"),
    "lim.alignment": ("Alignment checks that case identifiers are consistent, not that they refer to the "
                      "same images for every version.",
                      "照合で確認しているのは症例 ID の一貫性であり、すべてのバージョンで同じ画像を指していることまでは確認していない。"),
    "lim.argmax": ("Metrics are computed on the multiclass decision (argmax); no alternative decision "
                   "threshold is evaluated.",
                   "指標は多クラス判定（argmax）に基づいて計算しており、別の判定閾値は評価していない。"),

    # Report: what this report cannot establish
    "cannot.1": ("A non-significant result does not prove the absence of regression, equivalence or "
                 "non-inferiority.",
                 "有意でない結果は、性能低下がないこと、同等性、非劣性のいずれも証明しない。"),
    "cannot.2": ("This analysis is not a clinical validation, nor a demonstration of clinical safety.",
                 "本分析は臨床的妥当性確認ではなく、臨床上の安全性を示すものでもない。"),
    "cannot.3": ("This report does not certify compliance with ISO 13485, the FDA QMSR or any other "
                 "regulation.",
                 "本レポートは、ISO 13485、FDA QMSR、その他いかなる規制への適合も証明しない。"),
    "cannot.4": ("Synthetic sensitivity tests do not validate real clinical acquisition conditions.",
                 "合成データによる感度試験は、実際の臨床撮像条件での妥当性を示すものではない。"),
    "cannot.5": ("Near-duplicate detection alone does not prove data leakage or patient identity.",
                 "準重複の検出だけでは、データリークも患者の同一性も証明されない。"),
    "cannot.6": ("The conclusions are limited to the data, protocol, assumptions and methods actually used.",
                 "結論は、実際に使用したデータ、プロトコル、仮定、手法の範囲に限られる。"),

    # Web interface
    "web.local_only": ("local use · no data is sent to the Internet",
                       "ローカル専用 · データはインターネットに送信されません"),
    "web.footer": ("Technical evaluation aid. Not a medical device, not a clinical validation, not proof "
                   "of regulatory compliance.",
                   "技術評価の支援ツールです。医療機器ではなく、臨床的妥当性確認や規制適合の証明でもありません。"),
    "web.new_evaluation": ("New evaluation", "新しい評価"),
    "web.intro": ("Upload a TOML configuration and the CSV files it references. CSV file names must match "
                  "the paths in the configuration exactly, for example:",
                  "TOML 設定ファイルと、そこで参照している CSV ファイルをアップロードしてください。"
                  "CSV のファイル名は、設定ファイル内のパスと完全に一致している必要があります。例:"),
    "web.config_label": ("Configuration (.toml)", "設定ファイル（.toml）"),
    "web.csv_label": ("CSV files (ground truth, predictions A and B; {max} at most)",
                      "CSV ファイル（正解データ、バージョン A と B の予測。最大 {max} 個）"),
    "web.size_note": ("{mb} MB maximum per file. Files from a rejected evaluation are deleted immediately.",
                      "1 ファイルあたり最大 {mb} MB。受け付けられなかった評価のファイルは直ちに削除されます。"),
    "web.submit": ("Run the evaluation", "評価を実行"),
    "web.examples": ("Example files to download (synthetic data):", "ダウンロード用のサンプルファイル（合成データ）:"),
    "web.format_docs": ("File formats:", "ファイル形式の説明:"),
    "web.history": ("History", "履歴"),
    "web.col_date": ("Date (UTC)", "日時（UTC）"),
    "web.col_evaluation": ("Evaluation", "評価"),
    "web.col_versions": ("Versions", "バージョン"),
    "web.col_cases": ("Cases", "症例数"),
    "web.col_decision": ("Decision", "判定"),
    "web.rejected_row": ("evaluation rejected: {error}", "評価不可: {error}"),
    "web.no_history": ("No evaluations yet.", "評価はまだありません。"),
    "web.cases_n": ("{n} cases", "{n} 症例"),
    "web.col_criterion": ("Criterion", "基準"),
    "web.open_report": ("Open the Version Verification Record", "Version Verification Record を開く"),
    "web.download_report": ("Download the HTML report", "HTML レポートをダウンロード"),
    "web.report_note": ("The full report contains the metrics, intervals, confusion matrices, items not "
                        "provided, limitations and the section “What This Report Cannot Establish”. "
                        "Configuration SHA-256:",
                        "完全なレポートには、指標、信頼区間、混同行列、未提供の項目、分析の限界、"
                        "および「What This Report Cannot Establish（本レポートで立証できないこと）」の節が含まれます。"
                        "設定ファイルの SHA-256:"),
    "web.not_found_title": ("Not found", "見つかりません"),
    "web.not_found": ("This evaluation or file does not exist.", "この評価またはファイルは存在しません。"),
    "web.back_home": ("Back to home", "ホームに戻る"),
    "web.no_config": ("No configuration file (.toml) provided.", "設定ファイル（.toml）が指定されていません。"),
    "web.no_csv": ("No CSV file provided.", "CSV ファイルが指定されていません。"),
    "web.too_many_files": ("{n} CSV files provided; maximum {max}.",
                           "CSV ファイルが {n} 個指定されています（上限は {max} 個です）。"),
    "web.bad_filename": ("File name refused: {name} (letters, digits, . _ - only; no folder).",
                         "使用できないファイル名です: {name}（英字、数字、. _ - のみ使用でき、フォルダーは含められません）。"),
    "web.bad_extension": ("{name}: {extension} extension expected.", "{name}: 拡張子は {extension} にしてください。"),
    "web.duplicate_names": ("Duplicate file names: {names}.", "ファイル名が重複しています: {names}。"),
    "web.too_large": ("{name} exceeds {mb} MB.", "{name} が {mb} MB を超えています。"),
    "web.invalid_config": ("Invalid configuration: {error}", "設定が不正です: {error}"),
    "web.rejected": ("Evaluation rejected, no report produced.",
                     "評価は受け付けられませんでした。レポートは作成されていません。"),

    # Web interface: presentation, bundled demonstrations, public deployment
    "web.public_banner": ("public demo · research prototype · not for clinical use",
                          "公開デモ · 研究用プロトタイプ · 臨床使用不可"),
    "web.headline": ("Verify a new version of a medical image classifier",
                     "医用画像分類モデルの新バージョンを検証する"),
    "web.tagline": ("Is version B of a medical image classifier really better than version A, and is the "
                    "evidence strong enough to say so? MedVision QA answers from the predictions of both "
                    "versions on the same test cases, with acceptance criteria written in advance.",
                    "医用画像分類モデルのバージョン B は、本当にバージョン A より優れているのか。そう言えるだけの根拠はあるのか。"
                    "MedVision QA は、同じテスト症例に対する両バージョンの予測と、事前に定めた受け入れ基準から判定します。"),
    "web.feature_validation": ("Checks the input files and rejects every invalid row with its file, line and "
                               "column, instead of silently cleaning the data.",
                               "入力ファイルを検証し、不正な行はデータを黙って修正せず、ファイル・行・列を示してすべて報告します。"),
    "web.feature_intervals": ("Computes the metrics with bootstrap confidence intervals, resampled by "
                              "patient when patient identifiers are given.",
                              "指標をブートストラップ信頼区間付きで計算します。患者 ID がある場合は患者単位で再標本化します。"),
    "web.feature_decision": ("Applies the criteria (threshold, non-inferiority, superiority) to the interval "
                             "bounds only: SATISFIED, NOT_SATISFIED or INCONCLUSIVE.",
                             "基準（閾値、非劣性、優越性）を信頼区間の上下限のみに適用し、SATISFIED、NOT_SATISFIED、"
                             "INCONCLUSIVE のいずれかを返します。"),
    "web.feature_report": ("Produces a traceable report, the Version Verification Record, in English or "
                           "Japanese, with the SHA-256 of the data and configuration.",
                           "データと設定ファイルの SHA-256 を含む追跡可能なレポート（Version Verification Record）を、"
                           "英語または日本語で作成します。"),
    "web.try_title": ("Try it", "試してみる"),
    "web.demo_synthetic_title": ("Synthetic example", "合成データの例"),
    "web.demo_synthetic_text": ("Two simulated versions of a 4-class brain MRI classifier: 872 simulated "
                                "images, 450 simulated patients. No real patient.",
                                "4 クラスの脳 MRI 分類モデルの 2 つの模擬バージョン。模擬画像 872 枚、模擬患者 450 人。"
                                "実在の患者は含まれません。"),
    "web.demo_mri_title": ("Real brain MRI predictions", "実際の脳 MRI での予測"),
    "web.demo_mri_text": ("SimpleCNN versus ResNet18, trained on the public figshare brain tumour MRI "
                          "dataset (CC BY 4.0) and tested on 64 patients kept out of training.",
                          "公開データセット figshare 脳腫瘍 MRI（CC BY 4.0）で学習した SimpleCNN と ResNet18 を、"
                          "学習に使っていない 64 人の患者で比較します。"),
    "web.demo_rsna_title": ("Real chest X-ray predictions", "実際の胸部 X 線での予測"),
    "web.demo_rsna_text": ("Lung-opacity detector at 512 px versus 384 px (Faster R-CNN), RSNA Pneumonia "
                           "Detection Challenge, test split of 2,290 patients kept out of training.",
                           "肺野陰影の検出器（Faster R-CNN）の 512 px 版と 384 px 版を、RSNA Pneumonia Detection "
                           "Challenge の学習に使っていない 2,290 人の患者のテスト分割で比較します。"),
    "web.try_note": ("Each example is computed by the server when you open it (10 to 20 seconds the "
                     "first time), from the files committed in the repository.",
                     "各例は、リポジトリに含まれるファイルから、開いた時点でサーバーが計算します（初回は約 10～20 秒）。"),
    "web.demo_synthetic_note": ("Synthetic data generated by examples/synthetic_demo/generate.py: these "
                                "results describe no real model and no real patient.",
                                "examples/synthetic_demo/generate.py で生成した合成データです。"
                                "この結果は実在のモデルや患者を表すものではありません。"),
    "web.demo_mri_note": ("Predictions of two models trained by the author on the public figshare brain "
                          "tumour MRI dataset (CC BY 4.0), test set of 64 patients disjoint from training. "
                          "One public dataset from one source: this result says nothing about clinical "
                          "performance. Protocol, training and data audit: experiments/brain_mri on GitHub.",
                          "作成者が公開データセット figshare 脳腫瘍 MRI（CC BY 4.0）で学習した 2 つのモデルの予測です。"
                          "テストセットは学習と重複しない 64 人の患者です。単一の情報源による 1 つの公開データセットであり、"
                          "臨床性能については何も示しません。プロトコル、学習、データ監査: GitHub の experiments/brain_mri。"),
    "web.demo_rsna_note": ("Predictions of two lung-opacity detectors trained by the author on the RSNA "
                           "Pneumonia Detection Challenge data (Kaggle, non-commercial use), test split of "
                           "5,349 images from 2,290 patients disjoint from training; each image is scored by "
                           "its highest box score. One dataset from one source: this result says nothing about "
                           "clinical performance. Protocol, training and detection metrics: "
                           "experiments/rsna_pneumonia on GitHub.",
                           "作成者が RSNA Pneumonia Detection Challenge のデータ（Kaggle、非商用利用）で学習した 2 つの"
                           "肺野陰影検出器の予測です。テスト分割は学習と重複しない 2,290 人の患者の 5,349 枚で、各画像は"
                           "最も高いボックスのスコアで評価されます。単一の情報源による 1 つのデータセットであり、臨床性能"
                           "については何も示しません。プロトコル、学習、検出指標: GitHub の experiments/rsna_pneumonia。"),
    "web.public_notice": ("Public demonstration. Do not upload patient data. Uploaded files are evaluated in a "
                          "temporary folder deleted before the answer is sent; no history is kept.",
                          "公開デモです。患者データはアップロードしないでください。アップロードされたファイルは一時フォルダーで評価され、"
                          "応答の送信前に削除されます。履歴は保存されません。"),
    "web.public_limits": ("On this public demo: {mb} MB in total at most, and at most {max} bootstrap "
                          "resamples.",
                          "この公開デモでは、合計 {mb} MB まで、ブートストラップの再標本化は最大 {max} 回までです。"),
    "web.public_resamples": ("This public demo accepts at most {max} bootstrap resamples "
                             "([statistics] bootstrap_resamples). Run larger evaluations locally.",
                             "この公開デモで使えるブートストラップの再標本化は最大 {max} 回です"
                             "（[statistics] bootstrap_resamples）。より大きな評価はローカルで実行してください。"),
    "web.public_not_stored": ("Nothing was stored: download the reports now, they cannot be opened again "
                              "from this page later.",
                              "何も保存されていません。レポートは今ダウンロードしてください。後からこのページで開き直すことはできません。"),
    "web.download_report_en": ("Download the report (English)", "レポートをダウンロード（英語）"),
    "web.download_report_ja": ("Download the report (Japanese)", "レポートをダウンロード（日本語）"),
    "web.limits_title": ("Limits", "限界"),
    "web.limit_status": ("Research prototype written by one developer. Not a medical device, not clinically "
                         "validated, no regulatory clearance.",
                         "1 人の開発者による研究用プロトタイプです。医療機器ではなく、臨床的に妥当性確認されておらず、"
                         "規制上の承認もありません。"),
    "web.limit_predictions": ("It checks predictions it is given; it does not run a model on images. Its "
                              "conclusions are only as good as the test set behind them.",
                              "与えられた予測を検証するだけで、画像に対してモデルを実行することはありません。"
                              "結論の質は、その背後にあるテストセットの質を超えません。"),
    "web.limit_statistics": ("Small test sets give wide intervals, hence INCONCLUSIVE decisions. The DeLong "
                             "test is not implemented; AUROC differences use the paired bootstrap.",
                             "テストセットが小さいと信頼区間が広くなり、判定は INCONCLUSIVE になります。DeLong 検定は"
                             "実装しておらず、AUROC の差には対応のあるブートストラップを使います。"),
    "web.limit_open": ("The points still unverified are listed in docs/audit.md.",
                       "未検証の点は docs/audit.md に記載しています。"),
    "web.links": ("Source code, specification and audit:", "ソースコード、仕様、監査:"),
    "web.error_title": ("Something went wrong", "エラーが発生しました"),
    "web.error": ("The server could not complete this request. No result was produced. Try again, or "
                  "start from one of the examples.",
                  "サーバーはこの要求を完了できませんでした。結果は作成されていません。もう一度試すか、例から始めてください。"),
}

CATALOG = {lang: {key: texts[i] for key, texts in MESSAGES.items()} for i, lang in enumerate(LANGUAGES)}


def check_language(lang: str) -> str:
    if lang not in LANGUAGES:
        raise ValueError(f"Unsupported language: {lang!r} (supported: {list(LANGUAGES)}).")
    return lang


@dataclass(frozen=True)
class Text:
    """A message to render later: catalog key plus parameters.

    Parameter values are plain values, ``Text`` or tuples of ``Text`` (joined with the
    language's list separator).
    """

    key: str
    params: tuple = ()

    def render(self, lang: str = DEFAULT_LANGUAGE) -> str:
        values = {name: _render_value(value, lang) for name, value in self.params}
        return CATALOG[check_language(lang)][self.key].format(**values)

    def __str__(self) -> str:
        return self.render(DEFAULT_LANGUAGE)

    def to_dict(self) -> dict:
        return {"key": self.key, "params": {name: _dump(value) for name, value in self.params}}

    @classmethod
    def from_dict(cls, data: dict) -> "Text":
        return msg(data["key"], **{name: _load(value) for name, value in data["params"].items()})


def msg(key: str, **params) -> Text:
    if key not in MESSAGES:
        raise KeyError(f"Unknown message key: {key!r}")
    return Text(key, tuple(sorted((name, tuple(v) if isinstance(v, list) else v)
                                  for name, v in params.items())))


def raw(text: str) -> Text:
    """Text that is not in the catalog (e.g. a parser's own error message), shown as is."""
    return msg("raw", text=text)


def t(key: str, lang: str = DEFAULT_LANGUAGE, **params) -> str:
    return msg(key, **params).render(lang)


def _render_value(value, lang):
    if isinstance(value, Text):
        return value.render(lang)
    if isinstance(value, tuple) and value and all(isinstance(v, Text) for v in value):
        return CATALOG[lang]["sep"].join(v.render(lang) for v in value)
    return value


def _dump(value):
    if isinstance(value, Text):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_dump(v) for v in value]
    return value


def _load(value):
    if isinstance(value, dict):
        return Text.from_dict(value)
    if isinstance(value, list):
        return tuple(_load(v) for v in value)
    return value
