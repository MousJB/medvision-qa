# フェーズ 0 — 調査と範囲の確定

[English](../phase0_inspection.md)

日付: 2026-10-29

## 1. ローカル環境

| 項目 | 確認結果 |
|---|---|
| OS | Windows 10 Home 10.0.19045 |
| Python | 3.12.6（`C:\Python312`）、プロジェクトの仮想環境 `.venv/` |
| インストール済みの依存パッケージ | numpy 2.5.4、scipy 1.18.1、scikit-learn 1.9.1、pytest 9.2.0。正確なバージョンは `requirements-lock.txt` |
| git | 2.44.0。`main` でリポジトリを初期化、この時点ではコミットなし |
| R / pROC | **なし**: 現時点では DeLong 法を独立に検証できない（§ 4 を参照） |
| GPU | PATH に CUDA 12.3 あり。フェーズ 4 までは不要のため未確認 |

## 2. 候補リポジトリ: `MousJB/brain-tumor-mri-classification`

GitHub API で調査（読み取りのみ。クローンもデータのダウンロードもしていない）。

| 項目 | 確認結果 |
|---|---|
| コードのライセンス | MIT |
| 内容 | `src/dataset.py`、`src/models.py`、`src/utils.py`、`README.md`、`requirements.txt` |
| ノートブック | `notebooks/Brain_Tumor_Classification.ipynb` は**空**（2 バイト） |
| チェックポイント・予測 | リポジトリに**ない** |
| クラス | glioma、meningioma、no-tumor、pituitary。インデックスの順序は `Dataset` に渡す `classes` リストで決まるが、バージョン管理されたコードでは固定されていない |

### 影響

- README の結果（94.58%、98.09% など）は**リポジトリからは再現できない**。それを出力した
  ノートブックは空で、重みもバージョン管理されていない。MedVision QA の基準となる結果として
  使ってはならない。
- README には「validation accuracy」とあるが、データセットには `Training/` と `Testing/` の
  フォルダーしかない。検証用データの出所が記録されていない。再利用の前に明確にする必要がある
  （フェーズ 4）。
- `evaluate_model` は argmax だけを保持し、**スコアを出力しない**。AUROC のためには、softmax
  確率を [data_format.md](data_format.md) の形式で書き出す必要がある。
- 前処理についての所見（フェーズ 4 で確認。ここでは修正しない）: z スコアで標準化した後に、
  さらに画像を 255 で割っており、意図しない処理のように見える。

## 3. データセット: Kaggle「MRI Brain Tumor Dataset: 4-Class (7,023 Images)」

公開 Kaggle API で取得したメタデータ
（`mohamadabouali1/mri-brain-tumor-dataset-4-class-7023-images`、バージョン 1）。

| 項目 | 確認結果 |
|---|---|
| Kaggle で申告されたライセンス | MIT |
| 作成者 | Mohamad Abou Ali |
| サイズ | 約 139 MB |
| 「Blurred」「Noisy」「Patient Motion Artifact」セット | 作成者によれば**合成**データ |

### 未確認の点

- **画像の上流の来歴**: Kaggle の説明には、7,023 枚の画像の出所が書かれていない。過去の公開
  データセットに由来する場合、申告された MIT ライセンスだけでは元の権利は保証されない。公開の
  デモの前に、作成者が挙げている GitHub リポジトリや論文などで確認する必要がある。
- `Training/` と `Testing/` の間の完全重複・準重複: 未調査（フェーズ 4）。
- 患者 ID がないこと: その可能性が高いが要確認。`patient_id` がなければ、推論はすべて画像単位になる。

### レポートへの影響

Blurred、Noisy、Motion での結果は、実際の撮像条件での妥当性確認ではなく、**合成データによる
感度試験**として示す必要がある。

## 4. DeLong 法

R はインストールされていない。仕様書の第 7 節により、これはフェーズ 1 を妨げない。
決定（§ 6）: フェーズ 2 では対応のあるブートストラップを用い、DeLong 法は「未実装」と明記する。

## 5. フェーズ 0 での決定事項

| 項目 | 決定 |
|---|---|
| 入力形式 | [data_format.md](data_format.md): 正解データを別ファイルにする（推奨）、バージョンごとに予測 CSV を 1 つ、`case_id` による厳密な照合 |
| 設定と基準 | [evaluation_config.md](evaluation_config.md): TOML、基準は信頼区間で判定、平均をとらずに集約 |
| フォルダー構成 | `app/`（仕様書の第 11 節。参考扱い）ではなく `src/medvision_qa/`（インストール可能なパッケージ）。名前が汎用的でなく、テストと本番で import が同じになる。モジュールはフェーズごとに作成し、空のモジュールは作らない |
| 依存パッケージ | フェーズ 1 と 2 で使うもの（numpy、scipy、scikit-learn）のみ。FastAPI、Jinja2、SQLite はフェーズ 3/5 で追加 |
| CSV の読み込み | 暗黙の変換（`"NA"` → NaN、型推定）を避けるため、pandas ではなく標準の `csv` モジュールを使う予定。フェーズ 1 で確定 |

## 6. フェーズ 0 の終わりに決めた事項

| 問い | 決定 | 理由 |
|---|---|---|
| ライセンス | MIT（`LICENSE`） | MRI リポジトリと揃えるため。ポートフォリオとしても扱いやすい |
| 陽性クラス | `positive` = クラスの**リスト**。MRI のデモでは腫瘍（`glioma`、`meningioma`、`pituitary`）対 `notumor` | このデータセットで最も自然な臨床上の問い。1 クラスだけのリストにすれば一対他も可能 |
| 閾値による判定規則 | v0.1 では対応しない。`predicted_label` は argmax であること | あいまいなケースを減らすため。実際の必要が生じれば後で追加できる |
| DeLong 法 | 実装しない。フェーズ 2 では AUROC を対応のあるブートストラップで比較 | 独立した参照実装がない（R がない）。検証していない手法は公開しない |

## 7. フェーズ 0 の通過条件

| 条件 | 状態 |
|---|---|
| スキーマと範囲を文書化 | 完了: `docs/data_format.md`、`docs/evaluation_config.md` |
| 再現可能な環境 | `.venv` + `pyproject.toml` + `requirements-lock.txt` |
| 基本テストが実行可能 | `pytest`: 3 件成功（2026-10-29） |
| データのライセンスと権利 | 申告ライセンスは確認済み。**上流の来歴は未確認**。合成フィクスチャを使うフェーズ 1〜3 は妨げないが、フェーズ 4 の前提条件となる |
