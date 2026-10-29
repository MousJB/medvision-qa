# 評価設定、受入基準、メタデータ — v0.1

[English](../evaluation_config.md)

状態: フェーズ 0 で定義。読み込み・検証（`src/medvision_qa/config.py`）と判定エンジン
（`src/medvision_qa/decision_engine.py`）は**フェーズ 2 で実装**。メタデータはフェーズ 3
からレポートに表示されます。下の例は `tests/test_config.py` でそのまま読み込んで検証しています。

ファイルパス: **設定ファイルのあるフォルダーからの相対パス**で、そのフォルダーの外は
指定できません。絶対パスと `..` は拒否します（ディレクトリトラバーサル対策）。
ファイルは実在している必要があります。

形式: **TOML**（読みやすく、コメントを書け、標準ライブラリの `tomllib` で読めるため
依存パッケージが不要）。不明なキーはエラーにします。入力ミスによって基準が黙って
無効になるのを防ぐためです。

---

## 1. 完全な例

```toml
schema_version = "0.1"

[evaluation]
title = "SimpleCNN v1 対 v2 — 標準テスト"
objective = "v2 のマクロ F1 が v1 に劣らないことを確認する。"

[classes]
order = ["glioma", "meningioma", "notumor", "pituitary"]
positive = ["glioma", "meningioma", "pituitary"]   # 任意。腫瘍 対 notumor。感度・特異度・AUROC に必要

[data]
ground_truth_mode = "separate_file"   # または "embedded"
ground_truth_file = "ground_truth.csv"
description = "Kaggle MRI-BT、Testing/ フォルダー"
nature = "clinical"           # synthetic | clinical | not_provided（既定値）
manifest_sha256 = ""          # 空 = 未提供。レポートにもそのまま表示

[versions.A]
id = "simplecnn-v1"
predictions_file = "preds_v1.csv"
code_commit = ""              # 空 = 未提供。推測で埋めることはない
weights_sha256 = ""
preprocessing = "グレースケール、p1-p99 でクリッピング、z スコア、224×224"
description = ""

[versions.B]
id = "simplecnn-v2"
predictions_file = "preds_v2.csv"
code_commit = ""
weights_sha256 = ""
description = ""

[statistics]
confidence_level = 0.95
bootstrap_resamples = 2000
seed = 20261029               # 必須。既定値なし
probability_sum_tolerance = 1e-3

[sample_size]
status = "not_provided"       # provided | not_provided | not_applicable | based_on_data_availability
justification = ""            # provided または not_applicable の場合は必須

[[criteria]]
id = "C1"
description = "B のマクロ F1 が A に劣らない（マージン 0.02）"
kind = "non_inferiority"
metric = "macro_f1"
margin = 0.02

[[criteria]]
id = "C2"
description = "B の glioma の再現率が 0.90 以上"
kind = "absolute"
metric = "recall"
class = "glioma"
threshold = 0.90
```

---

## 2. 各フィールド

### 未提供の値

メタデータのフィールドが空（`""`）の場合は**未提供**を意味し、レポートには
「未提供（Not provided）」と表示されます。提供されていないコミット、ハッシュ、
モデル ID、来歴を、本ツールが計算したり推測したりすることは一切ありません。

### `data.nature`

`synthetic` の場合、レポートの冒頭に「合成データ」の注意書きを表示します。`clinical` は
実画像であることを示しますが、その代表性については何も示しません。`not_provided`
（既定値）はそのまま表示します。

### `[statistics]`

| フィールド | 規則 |
|---|---|
| `confidence_level` | 0 より大きく 1 より小さい数値 |
| `bootstrap_resamples` | 1000 以上の整数（それ未満ではパーセンタイルの境界が不安定すぎる） |
| `seed` | 整数、**必須**（シードがなければ再現できない） |
| `probability_sum_tolerance` | 0 より大きい数値 |

### `[sample_size]`（仕様書の第 9 節）

| `status` | `justification` | 表示 |
|---|---|---|
| `provided` | 必須（手法、仮定、パラメーター、参考文献） | 記載内容 |
| `not_provided` | 空にする | **未提供** |
| `not_applicable` | 必須（理由） | 記載内容 |
| `based_on_data_availability` | 任意 | 警告: *統計的な根拠ではない* |

実際のサンプルサイズは、常にこれとは別に表示されます。

### 自由記述の言語

タイトル、目的、説明は自由記述であり、レポートには記載どおりに表示されます。レポートを
すべて日本語にしたい場合は、これらを日本語で書き、`--lang ja` を付けて実行してください
（`examples/synthetic_demo/config.ja.toml` を参照）。

---

## 3. 受入基準

### 基準で使用できる指標（v0.1）

| `metric` | パラメーター | 必要なもの |
|---|---|---|
| `accuracy` | — | — |
| `macro_f1` | — | — |
| `precision`、`recall`、`f1` | `class` | — |
| `sensitivity`、`specificity` | — | `classes.positive`（派生二値タスク。[data_format.md](data_format.md#陽性クラス派生二値タスク) を参照） |
| `auroc` | — | `classes.positive` とスコア |

バージョン間の AUROC の比較には、対応のあるブートストラップを用います（フェーズ 2）。
DeLong 法は、検証に使える独立した参照実装がない（R が利用できない）ため、v0.1 では
実装していません。

これらの指標はすべて「値が大きいほど良い」ものです。

### 基準の種類と判定規則

判定はすべて、`confidence_level` の水準の**両側信頼区間**（ブートストラップ、
フェーズ 1/2）に基づいて行い、点推定値だけで判定することはありません。
表記: `[L, U]` = 信頼区間の下限と上限。

**`absolute`**: 1 つのバージョンの指標を閾値 `threshold` ∈ [0, 1] と比較する。任意のキー
`version = "A"` または `"B"`。既定値は、B が宣言されていれば B、なければ A。使用した
バージョンは結果に表示される。

| 条件 | 状態 |
|---|---|
| `L ≥ threshold` | `SATISFIED` |
| `U < threshold` | `NOT_SATISFIED` |
| それ以外 | `INCONCLUSIVE` |

**`non_inferiority`**（非劣性）: 差 `Δ = B − A`、マージン `margin > 0`:

| 条件 | 状態 |
|---|---|
| `L(Δ) > −margin` | `SATISFIED` |
| `U(Δ) < −margin` | `NOT_SATISFIED` |
| それ以外 | `INCONCLUSIVE` |

両側 95% 信頼区間の場合、これは α = 2.5% の片側検定に相当します。有意差がないことが
`SATISFIED` につながることは**決してありません**。

**`superiority`**（優越性）: 差 `Δ = B − A`:

| 条件 | 状態 |
|---|---|
| `L(Δ) > 0` | `SATISFIED` |
| `U(Δ) ≤ 0` | `NOT_SATISFIED` |
| それ以外 | `INCONCLUSIVE` |

**どの種類でも**、指標が未定義の場合（例: クラスが存在しない）、必要なデータがない場合
（AUROC のスコアがない）、信頼区間を計算できない場合、または信頼区間の**幅がゼロ**の場合
（[comparison.md の第 3 節](comparison.md#3-判定エンジン)を参照）は、理由を添えて
`INCONCLUSIVE` とします。

`non_inferiority` と `superiority` の基準には `[versions.B]` が必要です。`margin` は 0 より
大きく 1 より小さい値です。

### 総合判定への集約

| 条件 | 総合判定 |
|---|---|
| `NOT_SATISFIED` の基準が 1 つでもある | `NOT_SATISFIED` |
| そうでなく、`INCONCLUSIVE` の基準が 1 つでもある | `INCONCLUSIVE` |
| すべての基準が `SATISFIED` | `SATISFIED` |
| 基準が 1 つも定義されていない | エラー（基準のない評価では判定を出せない） |

平均や重み付けは行わず、各基準の結果を個別に示します。

---

## 4. 分析前に定めた基準について、本ツールが保証できること・できないこと

本ツールは設定ファイルの SHA-256 ハッシュと実行時刻を記録し、レポートに表示します。
しかし、結果が判明する前に基準が書かれたことを**証明することはできません**。推奨する
運用: 最初の実行の前に設定ファイルを git にコミットしておくこと。レポートにはハッシュが
表示されるため、レビュー担当者はそれをコミットと照合できます。
