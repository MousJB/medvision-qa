# フェーズ 4 — データソースと計画（準備段階）

[English](../phase4_data_sources.md)

日付: 2026-10-29。**実施内容は [experiments/brain_mri/README.ja.md](../../experiments/brain_mri/README.ja.md) を参照。**
以下のライセンスとメタデータは、この日付に公式 API（figshare、Kaggle、GitHub）から取得したものです。

## 1. 候補となるデータセット

| データセット | リンク | ライセンス（申告） | 内容 | `patient_id` | 想定する役割 |
|---|---|---|---|---|---|
| **figshare — Jun Cheng**（v8、2024-12-21） | https://figshare.com/articles/dataset/brain_tumor_dataset/1512427 · DOI `10.6084/m9.figshare.1512427.v8` | **CC BY 4.0**（figshare API で確認） | 造影 T1 強調画像 3,064 スライス、**233 患者**。髄膜腫 708、神経膠腫 1,426、下垂体腫瘍 930。腫瘍マスク、`cvind.mat`（5 分割交差検証のインデックス）、`.mat` 形式、約 880 MB | **あり**（`cjdata.PID`） | **主データ**: 患者単位で分割して 2 つのバージョンを学習し、患者単位のブートストラップで評価する |
| **Kaggle MRI-BT — Abou Ali** | https://www.kaggle.com/datasets/mohamadabouali1/mri-brain-tumor-dataset-4-class-7023-images · リポジトリ: https://github.com/Mohamad-AbouAli/MRIBrainTumorDataset | MIT（申告） | 7,023 画像、4 クラス（`notumor` を含む）＋**合成**の 3 セット（Blurred、Noisy、Motion）、約 139 MB | なし | `brain-tumor-mri-classification` リポジトリで使用したデータセット。Training/Testing の**重複監査**と、**合成データによる感度試験** |
| Kaggle — Masoud Nickparvar | https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset | CC BY 4.0（申告） | figshare + SARTAJ + Br35H を統合したもの。現行版は 7,200 画像（クラスごとに 1,400 / 400）。旧版は 7,023 画像 | なし | 来歴の参照先、代替候補 |
| SARTAJ | https://www.kaggle.com/datasets/sartajbhuvaji/brain-tumor-classification-mri | MIT（申告） | 上流のソース（4 クラス） | なし | 上流としてのみ |
| Br35H | https://www.kaggle.com/datasets/ahmedhamada0/brain-tumor-detection | **「Data files © Original Authors」**: オープンなライセンスではない | `notumor` クラスの上流ソース | なし | 上流としてのみ。**再配布しない** |

## 2. 来歴に関する所見

- **MRI-BT（Abou Ali）≈ Nickparvar の旧版: 可能性は高いが未確認。** 合計（7,023）と 4 クラスが
  同じで、`brain-tumor-mri-classification` の README には学習用画像が 5,712 枚と記載されている。
  Abou Ali の Kaggle の説明には上流ソースの記載がない。両データセットのファイルのハッシュを
  比較して確認する必要がある。
- そうであれば、`notumor` クラスはライセンスがオープンでない **Br35H** に由来する。Kaggle で
  申告されている MIT ライセンスだけでは権利は保証されない。したがって、このデータセットの画像、
  サムネイル、スクリーンショットは公開してはならず、リポジトリには集計値とハッシュのみを置く。
- figshare の画像は複数の統合データセットに含まれている。そのため、同じ画像や同じ患者の
  スライスが Training と Testing の両方に入っているおそれがある。
- IEEE DataPort の利用者コメントで、SARTAJ の神経膠腫にラベルの誤りがある可能性が指摘されて
  いる。個別の報告であり、確認はしていない。
- Abou Ali の「challenging」セットは、作成者によれば**合成**データである。これは感度試験であり、
  臨床条件を再現したものではない。

## 3. 計画案

1. **figshare（主データ）。** 4 つの zip と `cvind.mat` をダウンロードする（アカウント不要）。
   MATLAB v7.3 形式であれば（要確認）`h5py` で `.mat` を変換し、データのフィールドだけを読み込み、
   コードは実行しない。SHA-256 のマニフェストを作成する。学習・検証・テストへの分割は**患者単位**
   で行う。`cvind.mat` が患者単位かどうかも確認する。
2. **実際の 2 つのバージョン**を学習する（例: SimpleCNN と ResNet18、またはデータ拡張の有無で
   比較する ResNet18）。乱数シード、設定、重みのハッシュを記録する。手元の GPU（GTX 1650、
   4 GB）でも、バッチを小さくすれば十分である。
3. **softmax スコア**と `patient_id` を含めて予測を [data_format.md](data_format.md) の形式で
   書き出し、MedVision QA で評価する（単位: 患者）。
4. **MRI-BT（監査）。** Training と Testing の間で完全重複（SHA-256）と準重複（知覚ハッシュ）を
   調べ、検出された症例を目視で確認する。件数を報告するが、来歴の裏付けなしにデータリークと
   結論づけない。
5. 合成セットによる感度試験を、合成データであることを明示して行う。

## 4. 必要だったもの

| 項目 | 用途 | 2026-10-29 時点の状態 |
|---|---|---|
| 不要（公開ダウンロード） | figshare | 準備済み |
| Kaggle アカウントと API トークン（`%USERPROFILE%\.kaggle\kaggle.json`）、または手動ダウンロード | MRI-BT、Nickparvar | **なし**（`.kaggle` フォルダーなし） |
| 別環境の CUDA 対応 PyTorch と torchvision | 学習 | 要インストール（MedVision QA の依存パッケージには加えない） |
| 約 2 GB のディスク容量 | データと重み | 要確認 |
| ライセンスを踏まえた利用（ポートフォリオ、非商用）についての所有者の同意 | すべて | 要確認 |

## 5. `brain-tumor-mri-classification` リポジトリから再利用できないもの

ノートブックは空で、重みも予測もバージョン管理されておらず、評価ではスコアを残さず argmax
だけを保持している。そのため README の数値は再現できず、学習し直す必要がある。
`src/models.py` のコード（SimpleCNN、ResNet18）は再利用できる。
