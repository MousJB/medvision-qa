# MedVision QA

[![tests](https://github.com/MousJB/medvision-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/MousJB/medvision-qa/actions/workflows/tests.yml)

[English](README.md)

医用画像分類モデルのバージョンを比較検証し、技術的に記録するためのツールです。

同じ症例に対する 2 つのモデルバージョンの予測から、MedVision QA はデータを検証し、指標とその
不確実性を計算し、事前に定めた受入基準を適用して、HTML レポート
*Version Verification Record*（バージョン検証記録）を英語または日本語で作成します。

> **MedVision QA は医療機器ではありません。** 診断ツール、臨床的妥当性確認、規制適合
> （ISO 13485、FDA QMSR など）の証明のいずれでもありません。

## エンジニアリング上の方針

以下の設計上の選択は、いずれもコード、テスト、または git の履歴で確認できます。

| 選択 | 理由 | 根拠 |
|---|---|---|
| 不正な入力は修正せずに却下する | 黙って削除された行は、誰も気づかないまま指標を変えてしまう | すべての違反をファイル、行、列、規則とともに報告: [validation.py](src/medvision_qa/validation.py)、[tests/test_validation.py](tests/test_validation.py) |
| 症例は行の順番ではなく `case_id` で結合する | 順番の異なる 2 つのファイルでは、別の症例どうしを比較してしまう | 欠けている症例や余分な症例はエラー: [alignment.py](src/medvision_qa/alignment.py)、[tests/test_alignment.py](tests/test_alignment.py) |
| 基準は結果を見る前に書く | 結果を見てから閾値を選ぶと結論に偏りが生じる | MRI の基準は学習前にコミット `6de2a12` で確定。レポートには設定ファイルの SHA-256 を記録 |
| 判定には信頼区間の境界のみを使う | 点推定が閾値を上回っても証拠にはならない | 区間が閾値を含む → INCONCLUSIVE（SATISFIED にはならない）。非劣性には事前に定めたマージンが必要: [decision_engine.py](src/medvision_qa/decision_engine.py) |
| `patient_id` があれば患者単位で再標本化する | 同じ患者のスライスは独立ではなく、画像単位のブートストラップでは区間が狭すぎる | 合成データの例で区間が 2 倍以上狭くなることを確認: [tests/test_confidence_intervals.py](tests/test_confidence_intervals.py)。ペアがクラスター化している場合はマクネマー検定を無効化 |
| 定義できない指標は未定義のままにする | 0/0 を 0 に置き換えると、モデルが実際より悪く（または良く）見える | 未定義の値にはそれぞれ理由が付く: [docs/ja/metrics.md](docs/ja/metrics.md) |
| 結果を独立したコードで検証する | モデルを検証するツール自身も検証されるべき | 指標は scikit-learn と、マクネマー検定は手書きの正確検定と照合。MRI の結果は別途再計算: [docs/ja/audit.md](docs/ja/audit.md) |
| 検証されていないものは提供しない | 信頼できるように見せた未検証の検定は、ないよりも悪い | DeLong 法は未実装（独立した参照実装がないため）。AUROC の差にはペア・ブートストラップを使用 |
| すべてのレポートは追跡可能で再現可能 | 追跡できない結果は監査できない | データ、設定、重みの SHA-256、コミット、パッケージのバージョン、実行 ID を記録。レポートを再生成しても変わるのは実行 ID と日時のみ |
| 限界も出力の一部とする | 数値だけのレポートは過大な解釈を招く | すべてのレポートの最後に「What This Report Cannot Establish」。未解決の点は [docs/ja/audit.md](docs/ja/audit.md#4-未検証のまま残る事項) に列挙 |

自動テストはプッシュのたびに実行されます（Linux と Windows、Python 3.11 と 3.12）:
[.github/workflows/tests.yml](.github/workflows/tests.yml)。

## 実 MRI データでの結果

公開データセット figshare（CC BY 4.0）で 2 つのバージョンを学習し、患者単位で分離したテスト
セット（64 患者）で、学習前に定めた基準により評価した結果は **INCONCLUSIVE（判定保留）** でした。
ResNet18 は SimpleCNN に劣らず、AUROC も優れていますが、神経膠腫の感度（0.929、信頼区間
[0.865; 0.970]）は閾値 0.90 を満たすことを示せていません。データ監査では、figshare に重複した
患者 ID があること、また Kaggle の MRI-BT データセットでは**テスト画像の 16.5% が学習用データに
コピーされている**ことも判明しました。詳細:
[experiments/brain_mri/README.ja.md](experiments/brain_mri/README.ja.md)。レポート:
[日本語](experiments/brain_mri/figshare_eval/report.ja.html)、
[英語](experiments/brain_mri/figshare_eval/report.html)。

## デモ（合成データ）

Web インターフェース（ファイルのアップロード、結果、履歴、レポートのダウンロード。英語・日本語）:

```bash
python -m medvision_qa.web        # http://127.0.0.1:8000/?lang=ja を開く
```

デモ用のファイルはホームページからダウンロードできます。コマンドラインでは:

```bash
python -m medvision_qa examples/synthetic_demo/config.ja.toml -o reports/demo.ja.html --lang ja
python -m medvision_qa examples/synthetic_demo/config.toml -o reports/demo.html
```

[examples/synthetic_demo/](examples/synthetic_demo/) の CSV は**合成データ**です（450 患者、
872 枚の模擬画像）。`python examples/synthetic_demo/generate.py` でバイト単位まで同じものを
再生成できます。レポートにもその旨が注意書きとして表示されます。

## 使い方

TOML 設定ファイル（[例](docs/ja/evaluation_config.md#1-完全な例)）から:

```bash
python -m medvision_qa config.toml -o report.ja.html --lang ja
```

Python から:

```python
from medvision_qa.evaluation import run_evaluation
from medvision_qa.report import write_report

result = run_evaluation("config.toml")
print(result.decision.state, "-", result.decision.reason.render("ja"))
for c in result.decision.criteria:
    print(c.criterion.id, c.state, c.reason.render("ja"))
write_report(result, "report.ja.html", lang="ja")
```

入力が不正な場合は `ValidationError` が発生し、その `.issues` にすべての違反（ファイル、行、列、
値、規則）が含まれます。各違反は `issue.render("ja")` で日本語にできます。設定ファイルが不正な
場合は `ConfigError` が発生し、`exc.text.render("ja")` で日本語のメッセージを得られます。

### 入力と出力の例

入力: 正解ファイル 1 つと、バージョンごとの予測ファイル 1 つ。`case_id` で結合します（行の順番では
結合しません）。規則の詳細: [docs/ja/data_format.md](docs/ja/data_format.md)。

```text
ground_truth.csv                     preds_v2.csv
case_id,true_label,patient_id        case_id,predicted_label,score_glioma,score_meningioma,score_notumor,score_pituitary
img_00000,meningioma,P0000           img_00000,pituitary,0.077062,0.382078,0.050313,0.490547
img_00001,glioma,P0001               img_00001,notumor,0.253126,0.177946,0.346870,0.222058
```

データが正しい場合の出力: コンソールに判定、そして HTML レポート（コンソール出力は英語）。

```text
$ python -m medvision_qa examples/synthetic_demo/config.toml -o reports/demo.html
SATISFIED — all 3 criteria are satisfied
Report: reports/demo.html
```

データが不正な場合の出力（ここでは `case_id` の重複と 1.2 のスコア）: 終了コード 2、レポートは作成されません。

```text
Invalid data, no report produced.
2 validation issue(s):
  - [unique_case_id] preds_v2.csv, line 4, column 'case_id': case_id already present on line 2 (value: 'img_00000')
  - [score_in_bounds] preds_v2.csv, line 3, column 'score_glioma': score outside [0, 1] (value: '1.2')
```

レポートは自己完結型の HTML ファイルです（スクリプトも外部リソースもなし）。GitHub ではソース
コードとして表示されるため、ダウンロードしてブラウザーで開いてください。

## アーキテクチャ

```text
config.toml ─► config.py            TOML の厳密な読み込み: クラス、バージョン、統計設定、基準
CSV ファイル ─► validation.py        すべての違反を収集し、行の削除や修正はしない
               alignment.py         case_id で結合。欠けている症例や余分な症例はエラー
               metrics.py           混同行列、クラス別・二値タスクの指標、AUROC
               confidence_intervals.py   パーセンタイル・ブートストラップ（patient_id があれば患者単位）
               comparison.py        B − A のペア・ブートストラップ、正確マクネマー検定（適用可能な場合）
               decision_engine.py   信頼区間の境界のみから SATISFIED / NOT_SATISFIED / INCONCLUSIVE
               evaluation.py        上記の手順を実行し、実行 ID、日時、パッケージのバージョンを記録
               report.py + templates/   Version Verification Record（HTML、英語または日本語）
               web.py + history.py  ローカル FastAPI インターフェース、SQLite 履歴
               duplicates.py        完全重複（SHA-256）と準重複（pHash）の検出
```

主な依存関係: numpy、scipy、Jinja2、scikit-learn（指標の計算コードでは使わず、テストで独立した
参照実装として使い、レポートにそのバージョンを記録する）。Web インターフェースには FastAPI、
uvicorn、python-multipart が加わります。

## ドキュメント

- [MEDVISION_QA.ja.md](MEDVISION_QA.ja.md): 仕様書の全文
- [docs/ja/data_format.md](docs/ja/data_format.md): 入力 CSV の形式と検証規則
- [docs/ja/metrics.md](docs/ja/metrics.md): 指標の定義、未定義になる条件、ブートストラップ、限界
- [docs/ja/evaluation_config.md](docs/ja/evaluation_config.md): 設定、受入基準、判定規則
- [docs/ja/comparison.md](docs/ja/comparison.md): 対応のある A/B 比較、マクネマー検定、DeLong 法の状態、追跡可能性
- [docs/ja/report.md](docs/ja/report.md): Version Verification Record の内容、保証している性質、言語
- [docs/ja/web.md](docs/ja/web.md): Web インターフェース、ローカルの保存先、セキュリティ対策
- [docs/ja/phase0_inspection.md](docs/ja/phase0_inspection.md): 環境、MRI リポジトリ、データセットの調査
- [docs/ja/phase4_data_sources.md](docs/ja/phase4_data_sources.md): データソースとライセンス
- [docs/ja/audit.md](docs/ja/audit.md): 2026-10-29 の監査: 実行したコマンド、独立した検証、所見、未検証の事項、デモの手順

## インストール（開発用）

Python 3.11 以上。CI で Ubuntu と Windows（Python 3.12、ロックした依存関係）、および Ubuntu の
Python 3.11（最新の依存関係）でテスト済み。開発環境は Windows 10、Python 3.12.6。

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"      # ライブラリ + Web インターフェース + テストツール
pytest
```

`pip install -e .` のみの場合は、FastAPI を含まないコア部分（検証、統計、レポート、コマンドライン）
をインストールします。`[web]` を付けるとインターフェースが加わります。

テスト済みの環境を正確に再現するには、`pip install -r requirements-lock.txt` の後に
`pip install -e . --no-deps` を実行します。

## データとセキュリティ

- ローカルでのみ実行します。データの分析のために、ネットワーク、LLM、外部 API を呼び出すことは
  ありません。Web インターフェースは `127.0.0.1` でのみ待ち受け、認証機能がないため、ネットワーク
  に公開してはいけません。
- データセットは同梱せず、自動でダウンロードすることもありません。`.gitignore` で `data/`、
  医用画像、モデルの重みを除外しています。
- pickle ファイルやモデルは読み込みません。読み込むのは CSV と TOML 設定ファイルのみです。
- テストには合成データを使い、常に合成データであることを明示しています。

## 言語

コード、メッセージ、ドキュメントは英語です。生成される出力（HTML レポート、Web インターフェース、
検証エラーや設定エラー）はすべて日本語でも利用でき、1 つのメッセージカタログ
（[src/medvision_qa/i18n.py](src/medvision_qa/i18n.py)）で管理しています。このプロジェクトは
当初フランス語で書かれました。翻訳コミットより前の git 履歴にフランス語の原文が残っています。
