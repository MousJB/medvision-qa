# figshare MRI 実験のプロトコル — 学習前に確定

[English](PROTOCOL.md)

日付: 2026-10-29。本文書と `figshare_eval/config.toml` は、最初の学習を行う**前**にコミット
しました（コミット `6de2a12`。原文はフランス語）。その後の変更点はすべて `README.ja.md` に
記載しています。この日本語訳は、規則を何も変更していません。

## データ

- figshare「brain tumor dataset」、Jun Cheng、v8、CC BY 4.0。ダウンロードは MD5 で検証
  （`download_figshare.py`）。
- 3,064 スライス、233 患者、3 クラス（glioma、meningioma、pituitary）。`case_id` = `.mat`
  ファイルの番号、`patient_id` = `cjdata.PID`。

## 分割

- **患者単位**で、クラスごとに層別化する。各患者の腫瘍は 1 種類のみ。1 人の患者が複数の
  クラスで現れた場合は、その異常を報告し、記録したうえでその患者を除外する。
- 患者の 60% を学習用、10% を検証用、30% をテスト用とする。乱数シード 20261029。
- テストセットは最終的な予測を出すために 1 回だけ使う。テストセットで調整は行わない。

## モデル（2 つのバージョン）

| バージョン | モデル | 学習 |
|---|---|---|
| A | SimpleCNN（`MousJB/brain-tumor-mri-classification` のアーキテクチャ） | ゼロから学習 |
| B | ImageNet で事前学習した torchvision の ResNet18 | 全層を学習 |

共通の手順: Adam（学習率は A が 1e-3、B が 1e-4）、最大 15 エポック、バッチサイズ 32、
交差エントロピー損失、軽いデータ拡張（左右反転、± 10° の回転）。**採用するチェックポイントは、
検証データのマクロ F1 が最も高いもの**とする。乱数シード 20261029、cuDNN の決定論的モード。

## 出力

- `figshare_eval/ground_truth.csv`（`case_id`、`true_label`、`patient_id`）。
- `figshare_eval/preds_*.csv`（`predicted_label` = argmax、`score_*` = softmax）。
- 重みの SHA-256、学習設定、ライブラリのバージョンを `figshare_eval/training_*.json` に記録。
- `figshare_eval/config.toml` で生成した MedVision QA のレポート。

## 受入基準

`figshare_eval/config.toml` を参照（C1: マクロ F1 の非劣性、マージン 0.03。C2: 神経膠腫の
感度 ≥ 0.90。C3: 神経膠腫の AUROC の優越性）。
