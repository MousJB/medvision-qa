# RSNA 肺野陰影：Faster R-CNN 512 px 対 384 px

[English](README.md)

作成者が [RSNA Pneumonia Detection Challenge](https://www.kaggle.com/competitions/rsna-pneumonia-detection-challenge)
のデータで学習した 2 つの肺野陰影検出器の、MedVision QA による評価です。学習、プロトコル、
検出指標は専用のリポジトリ [cxr-pneumonia-detection](https://github.com/MousJB/cxr-pneumonia-detection)
にあります。このフォルダーには、その MedVision QA 用ファイルのコピー（同じバイト列、同じ SHA-256）
を置いています。

> 研究目的のプロジェクトであり、**医療機器ではなく**、臨床的な検証も行っていません。単一の情報源に
> よる 1 つのデータセットであり、この結果は臨床性能については何も示しません。

## 比較するもの

- **A** `frcnn-r50-fpn-512`：torchvision Faster R-CNN ResNet-50 FPN、COCO 重み、入力 512 px。
- **B** `frcnn-r50-fpn-384`：同じモデル、学習方法、シード、予算。入力 384 px（唯一の変更点）。

学習前に定めた基準（cxr リポジトリの事前登録プロトコル）：B の AUROC（C1）、感度（C2）、
特異度（C3）が A に劣らないこと、マージンはそれぞれ 0.02、0.05、0.05。テスト分割：2,290 人の
患者の 5,349 枚（陰影あり 1,207 枚）、学習用・検証用と重複せず、1 回のみ評価。患者単位の
ブートストラップ（2,000 回、シード 20261030）。

MedVision QA は画像単位で評価するため、各画像のスコアは最も高いボックスのスコアとし、検証で
選んだ閾値 τ が 0.5 になるように変換しています（スコア ≥ τ なら `predicted_label = opacity`）。
ボックス単位のコンペティション指標は cxr リポジトリに記載しており、ここでは扱いません。

## 結果：SATISFIED（3 つの基準すべて）

| 画像単位 | A、512 px | B、384 px | B − A [95 % CI] |
|---|---|---|---|
| AUROC | 0.8883 | 0.8889 | +0.0006 [−0.0027, +0.0038] |
| τ における感度 | 0.6835 | 0.7117 | +0.0282 [+0.0084, +0.0512] |
| τ における特異度 | 0.8725 | 0.8590 | −0.0135 [−0.0202, −0.0068] |

数値は Version Verification Record によります。cxr リポジトリ独自のブートストラップ
（`scripts/evaluate.py`、[test_results.md](test_results.md)）では、点推定値は同じで、区間はわずかに
異なります（B − A の区間の差は最大 0.002。再標本化のコードが異なるため）。同ファイルにはボックス単位の
コンペティション指標も記載しています（A 0.2053、B 0.2190、B − A +0.0137 [+0.0040, +0.0238]：非劣性、マージン 0.02）。レポート：
[日本語](report.ja.html)、[英語](report.html)。

B の特異度は低い（区間はゼロを含まない）ものの、事前登録したマージン 0.05 の範囲内です。
同じ τ = 0.80 において、B は A より多くの画像を陽性と判定します。AUROC は変わりません。

## ファイル

| ファイル | 内容 |
|---|---|
| `config.toml` | 評価の設定（cxr リポジトリとバイト単位で同一） |
| `config.ja.toml` | 同じ値、自由記述は日本語 |
| `medvision/ground_truth.csv` | `case_id`、ラベル、NIH の患者、撮影方向、性別、年齢（画像なし） |
| `medvision/preds_r50_512.csv`、`medvision/preds_r50_384.csv` | A と B の画像単位の予測 |
| `report.html`、`report.ja.html` | cxr リポジトリで生成した Version Verification Record（同リポジトリでは `reports/vvr_en.html`、`reports/vvr_ja.html`） |
| `test_results.md` | cxr リポジトリのテストの全表（ボックス指標、誤り分析、英語） |

データ：RSNA Pneumonia Detection Challenge のコンペティション規約（非商用利用に限る、画像の
再配布禁止）。画像は含まれていません。

## レポートの再現

```bash
python -m medvision_qa experiments/rsna_pneumonia/config.ja.toml -o reports/rsna.ja.html --lang ja
python -m medvision_qa experiments/rsna_pneumonia/config.toml -o reports/rsna.html
```

Web インターフェースの `/demo/rsna-pneumonia` でも表示されます。
