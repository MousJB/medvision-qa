# 実 MRI データでの実験: figshare（Jun Cheng）、2 つのバージョン、MedVision QA による評価

[English](README.md)

学習前に確定したプロトコル: [PROTOCOL.ja.md](PROTOCOL.ja.md) と
[figshare_eval/config.toml](figshare_eval/config.toml)（コミット `6de2a12`）。データソースと
ライセンス: [docs/ja/phase4_data_sources.md](../../docs/ja/phase4_data_sources.md)。

> データ: figshare「brain tumor dataset」、Jun Cheng、v8、**CC BY 4.0**、
> DOI [10.6084/m9.figshare.1512427.v8](https://doi.org/10.6084/m9.figshare.1512427.v8)。
> 画像はバージョン管理しておらず、ID、ハッシュ、集計値のみを置いています。

## 再現手順

```bash
python -m venv .venv-train
.venv-train\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
.venv-train\Scripts\python -m pip install h5py pillow kagglehub numpy scipy
.venv-train\Scripts\python -m pip install -e . --no-deps

.venv-train\Scripts\python experiments/brain_mri/download_figshare.py     # MD5 を検証
.venv-train\Scripts\python experiments/brain_mri/prepare_figshare.py      # PNG、マニフェスト、分割、監査
.venv-train\Scripts\python experiments/brain_mri/train.py simplecnn
.venv-train\Scripts\python experiments/brain_mri/train.py resnet18
python -m medvision_qa experiments/brain_mri/figshare_eval/config.toml -o experiments/brain_mri/figshare_eval/report.html
python -m medvision_qa experiments/brain_mri/figshare_eval/config.ja.toml -o experiments/brain_mri/figshare_eval/report.ja.html --lang ja
```

## 1. データの準備と監査

| 項目 | 結果 |
|---|---|
| ファイル | `.mat` ファイル 3,064 個（MATLAB v7.3 / HDF5）。h5py で `label`、`PID`、`image` のフィールドのみ読み込み |
| サイズ | 512×512 が 3,049 枚、256×256 が 15 枚 |
| 元の PID | 233 個。2 つのクラスにまたがる PID はなし |
| 完全重複（画素） | **0** |
| 準重複（pHash、距離 ≤ 4） | 724 ペア。大半は同じ患者の隣接スライス |

### 所見: 1 人の患者が複数の PID を持つ

`MR<番号><英字>` 形式の PID（43 個、すべて神経膠腫）は、**語幹を共有する 18 のグループ**を
形成しています（例: `MR024780B`、`D`、`E`、`G`）。元の PID のまま分割すると、**12 のグループが
学習用・検証用・テスト用にまたがっていました。**

目視確認（確認用の一覧画像は `data/inspection/` にあり、バージョン管理外）: `MR024780D`（テスト）
と `MR024780E`（学習）のスライスはほぼ同一でした（同じ頭部、同じ病変）。`MR049453` /
`MR049453B`、`MR051644B` / `MR051644C`、`MR040240` / `MR040240D` も同じ解剖構造と同じ病変を
示しており、違いは撮影日が異なる検査として説明できる程度でした。これは放射線科医による読影では
ありません。

**決定（プロトコルからの変更。学習前に決定）**: 患者 = PID の語幹とします。これにより 209 患者と
なり、分割は **125 / 20 / 64 患者**（1,996 / 292 / 776 画像）になりました。慎重な選択です。
2 人の患者を誤って統合しても標本が小さくなるだけですが、分けたままにするとテストセットへの
リークのおそれがあるためです。受入基準は変更していません。

### 異なる患者間の準重複: 誤検出

統合後、異なる患者を結ぶペアが 69 あり、そのうち 38 は異なるセット間のペアでした。**38 ペアを
すべて確認しました。** 病変、頭部、コントラストはいずれも異なり、似ているのはスライスの向き
（正中矢状断、軸位断）だけでした。うち 11 ペアは髄膜腫と神経膠腫の組み合わせです。閾値 4 の
pHash は脳 MRI には緩すぎます。類似を示すだけで、何も証明しません。

詳細: [figshare_eval/data_audit.json](figshare_eval/data_audit.json)、
[figshare_eval/manifest.csv](figshare_eval/manifest.csv)。

## 2. Kaggle MRI-BT データセットの監査（`brain-tumor-mri-classification` で使用したもの）

スクリプト: [audit_mri_bt.py](audit_mri_bt.py)。結果:
[mri_bt_audit/summary.json](mri_bt_audit/summary.json) と
[mri_bt_audit/flagged_pairs.csv](mri_bt_audit/flagged_pairs.csv)（ファイル名のみ。Br35H の
ライセンスがオープンでないため、画像はバージョン管理していません）。対象: 元の BT-MRI セット
（Training 5,712、Testing 1,311、すべて 224×224）。「Challenging」セットは、同じ画像を劣化させた
ものであるため除外しています。

| 所見 | 値 |
|---|---|
| **バイト単位で同一**のファイルのグループ | 300（695 ペア） |
| **Training ↔ Testing** で同一のペア | 365 |
| **Training に同一のコピーがある Testing の画像** | **1,311 枚中 216 枚（16.5%）**: 髄膜腫 106、腫瘍なし 105、下垂体腫瘍 5（2026-10-29 に独立に再集計） |
| ラベルが異なる完全重複 | 0 |
| ラベルが異なる準重複（pHash ≤ 4） | 50。**24 ペアを確認**: すべて異なる画像であり誤検出（残り 26 ペアは未確認） |
| figshare の画像に近い MRI-BT の画像（pHash ≤ 4） | 1,704（主に Training の髄膜腫と下垂体腫瘍）。98% のペアでラベルが一致 |

**言えること。** MRI-BT のテスト画像の 16.5% は、学習用画像の完全なコピーです。したがって、
この Training/Testing の分割での評価は、これらの画像について独立ではありません。この分割で
公表された性能（`brain-tumor-mri-classification` の README の数値を含む。README にはその旨を
追記済み）は、おそらく楽観的です。この偏りの大きさは測定していません。

**言えないこと。** ファイルが同一であることは画像が同一であることを示しますが、患者が同一である
ことは示しません。MRI-BT には `patient_id` がないため、同じ患者の別のスライスが両方のセットに
分かれて入っているかどうかは確認できません。figshare との一致（1,704 画像）は、figshare を含む
統合データセットであるという仮説と矛盾しませんが、それだけで証明にはなりません。

## 3. 2 つのバージョンの学習

| | A — SimpleCNN | B — ResNet18（ImageNet） |
|---|---|---|
| 最良エポック（検証データのマクロ F1） | 13（0.850） | 15（0.954） |
| 所要時間（GTX 1650） | 169 秒 | 196 秒 |
| 重みの SHA-256 | `7b17a4a3…5127d2` | `a8901dd2…25d73f5` |
| 完全なログ | [training_simplecnn.json](figshare_eval/training_simplecnn.json) | [training_resnet18.json](figshare_eval/training_resnet18.json) |

環境: torch 2.14.1+cu126、torchvision、Python 3.12.6。重みはバージョン管理しておらず、
`data/models/` に置き、SHA-256 で識別しています。

**コード。** 学習ログには `code_commit = dedb768` と記録されています。これは実行時点の HEAD で
したが、`train.py` はまだコミットされていませんでした。実行したコードは変更なしで `2bcfb77` に
コミットしました（改行コードを正規化したうえで SHA-256 により同一内容であることを確認）。
`config.toml` で申告しているのはこのコミットです。

**部分的な決定性。** 乱数シードを固定し、決定論的アルゴリズムを要求しています（`warn_only`）が、
一部の CUDA 演算には決定論的な実装がありません。そのため、学習し直すと重みがわずかに異なる
可能性があります。

## 4. MedVision QA による評価（テスト: 776 スライス、64 患者）

レポート: [figshare_eval/report.html](figshare_eval/report.html)（英語）と
[figshare_eval/report.ja.html](figshare_eval/report.ja.html)（日本語）。95% 信頼区間、
**患者単位**のパーセンタイル・ブートストラップ（64 単位）、2,000 回の抽出。

| 基準（学習前に確定） | 結果 | 状態 |
|---|---|---|
| C1 — B のマクロ F1 が A に劣らない（マージン 0.03） | Δ = +0.129、信頼区間 [0.074; 0.188] | **SATISFIED** |
| C2 — B の神経膠腫の感度 ≥ 0.90 | 0.929、信頼区間 [0.865; 0.970] | **INCONCLUSIVE** |
| C3 — B の神経膠腫の AUROC が A を上回る | 0.916 → 0.990、Δ の信頼区間 [0.031; 0.135] | **SATISFIED** |
| **総合判定** | | **INCONCLUSIVE** |

| 指標 | A — SimpleCNN | B — ResNet18 |
|---|---|---|
| Accuracy | 0.800 [0.730; 0.860] | 0.928 [0.875; 0.968] |
| マクロ F1 | 0.795 [0.717; 0.851] | 0.923 [0.867; 0.964] |
| 再現率 神経膠腫 / 髄膜腫 / 下垂体腫瘍 | 0.800 / 0.750 / 0.835 | 0.929 / 0.934 / 0.923 |
| 特異度（神経膠腫 対 その他） | 0.844 | 0.969 |
| AUROC（神経膠腫 対 その他） | 0.916 | 0.990 |

**読み方。** このデータでは、B は A より明らかに優れています。しかし **C2 は示されていません**。
神経膠腫の感度の推定値（0.929）は 0.90 を上回っていますが、64 患者での信頼区間はまだ 0.90 を
含んでいます。点推定値だけで「合格」とするのは過大な解釈であり、INCONCLUSIVE という状態は
それを防ぐためのものです。結論を出すには、テスト患者を増やすか、それに見合った基準とサンプル
サイズの根拠を定める必要があります。

マクネマー検定は**適用できません**（患者あたり複数のスライスがあるため）。DeLong 法は実装して
おらず、AUROC の差は対応のあるブートストラップで求めています。

## 5. 限界

- データセットは 1 つのみ（中国の 2 病院、2005〜2010 年の撮像、造影 T1 強調画像）。外部検証は
  しておらず、結果は他の撮像条件には当てはまりません。
- PID の統合は、専門家ではない目視確認に基づく仮定（語幹が同じ = 同じ患者）に依存しています。
- 検証用データは 20 患者: エポックの選択はノイズが大きくなります（A の検証データのマクロ F1 は
  エポックによって 0.54 から 0.85 まで変動）。
- 画像ごとの min-max 変換と 224×224 へのリサイズで情報が失われます。ハイパーパラメーターの調整は
  しておらず、2 つのアーキテクチャを最適化して比較したものではありません。
- これらのモデルに対する頑健性試験はしていません。MRI-BT の「Challenging」セットは 4 クラス
  （notumor を含む）で、figshare の 3 クラスのタスクとは対応しません。
- これらの分析はいずれも臨床的妥当性確認ではありません。

## 6. 翻訳についての注記

リポジトリは評価の後でフランス語から英語に翻訳し、日本語版を追加しました。変更したのは自由記述の
テキストのみです: コメント、メッセージ、`config.toml` 内の説明、`training_*.json` の説明用
フィールド（`augmentation`、`selection`、`determinism`）、`mri_bt_audit/summary.json` の
「within」キー。数値、ハッシュ、基準、閾値はすべて変更していません。元のフランス語のファイルは
git の履歴（コミット `3a387f5` 以前）に残っています。レポートは翻訳後の設定ファイルから
再生成したため、設定ファイルのハッシュはコミット `6de2a12` のものとは異なります。
`config.ja.toml` は `config.toml` の日本語版で、数値は同一です（`report.ja.html` の生成に使用）。
