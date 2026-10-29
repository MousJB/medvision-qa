# Phase 4 — Sources de données et plan (préparation)

Date : 2026-10-29. Rien n'a encore été téléchargé. Les licences et métadonnées ci-dessous
ont été lues via les API officielles (figshare, Kaggle, GitHub) à cette date.

## 1. Datasets candidats

| Dataset | Lien | Licence (déclarée) | Contenu | `patient_id` | Rôle proposé |
|---|---|---|---|---|---|
| **figshare — Jun Cheng** (v8, 2024-12-21) | https://figshare.com/articles/dataset/brain_tumor_dataset/1512427 · DOI `10.6084/m9.figshare.1512427.v8` | **CC BY 4.0** (vérifiée via l'API figshare) | 3 064 coupes T1 avec gadolinium, **233 patients** ; méningiome 708, gliome 1 426, hypophyse 930 ; masques tumoraux ; `cvind.mat` (indices de validation croisée 5 plis) ; fichiers `.mat` ; ~880 Mo | **oui** (`cjdata.PID`) | **Principal** : entraîner 2 versions avec une séparation par patient, puis évaluer avec bootstrap par patient |
| **Kaggle MRI-BT — Abou Ali** | https://www.kaggle.com/datasets/mohamadabouali1/mri-brain-tumor-dataset-4-class-7023-images · dépôt : https://github.com/Mohamad-AbouAli/MRIBrainTumorDataset | MIT (déclarée) | 7 023 images, 4 classes (dont `notumor`) + 3 jeux **synthétiques** (Blurred, Noisy, Motion) ; ~139 Mo | non | Celui de ton dépôt IRM : **audit des doublons** Training/Testing et **tests de sensibilité synthétiques** |
| Kaggle — Masoud Nickparvar | https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset | CC BY 4.0 (déclarée) | Assemblage de figshare + SARTAJ + Br35H. Version actuelle : 7 200 images (1 400 / 400 par classe). Une version antérieure en comptait 7 023 | non | Référence de provenance ; alternative |
| SARTAJ | https://www.kaggle.com/datasets/sartajbhuvaji/brain-tumor-classification-mri | MIT (déclarée) | Source amont (4 classes) | non | Amont uniquement |
| Br35H | https://www.kaggle.com/datasets/ahmedhamada0/brain-tumor-detection | **« Data files © Original Authors »** : pas une licence ouverte | Source amont de la classe `notumor` | non | Amont uniquement : **ne pas redistribuer** |

## 2. Constats de provenance

- **MRI-BT (Abou Ali) ≈ Nickparvar, première version : probable, non confirmé.** Même
  total (7 023), mêmes 4 classes, et ton README indique 5 712 images d'entraînement. La
  description Kaggle d'Abou Ali ne cite pas ses sources amont. À confirmer en comparant les
  hashes des fichiers des deux datasets.
- Si c'est le cas, la classe `notumor` vient de **Br35H**, dont la licence n'est pas
  ouverte. La licence MIT déclarée sur Kaggle ne suffit pas à garantir les droits. Il ne
  faut donc pas publier d'images, de vignettes ni de captures d'écran de ce dataset.
  Seuls des agrégats et des hashes peuvent figurer dans le dépôt.
- Les images figshare apparaissent dans plusieurs de ces assemblages : il y a un risque de
  doublons, ou de coupes d'un même patient, à la fois en Training et en Testing.
- Un commentaire d'utilisateur sur IEEE DataPort signale de possibles erreurs d'étiquette
  dans les gliomes de SARTAJ. C'est anecdotique et non vérifié.
- Les jeux « challenging » d'Abou Ali sont **synthétiques**, selon leur auteur. Ce sont
  des tests de sensibilité, pas des conditions cliniques.

## 3. Plan proposé

1. **figshare (principal).** Télécharger les 4 zip et `cvind.mat` (sans compte). Convertir
   les `.mat` avec `h5py` si c'est le format MATLAB v7.3 (à vérifier), en lisant uniquement
   les champs de données, sans exécuter de code. Construire un manifeste SHA-256.
   Séparation train/val/test **par patient**. Vérifier si `cvind.mat` est par patient.
2. Entraîner **deux versions réelles** (par ex. SimpleCNN et ResNet18, ou ResNet18 avec et
   sans augmentation), avec graines, configurations et hashes des poids enregistrés. Le GPU
   local (GTX 1650, 4 Go) suffit avec de petits lots.
3. Exporter les prédictions **avec les scores softmax** et `patient_id`, au format de
   [data_format.md](data_format.md). Évaluer avec MedVision QA (unité : patient).
4. **MRI-BT (audit).** Doublons exacts (SHA-256) et quasi-doublons (hash perceptuel) entre
   Training et Testing, puis inspection manuelle des cas signalés. Rapporter les comptes,
   sans conclure à une fuite de données sans preuve de provenance.
5. Tests de sensibilité sur les jeux synthétiques, présentés comme tels.

## 4. Ce qui est nécessaire

| Élément | Pour | État |
|---|---|---|
| Rien (téléchargement public) | figshare | prêt |
| Compte Kaggle + jeton API (`%USERPROFILE%\.kaggle\kaggle.json`) ou téléchargement manuel | MRI-BT, Nickparvar | **absent** (aucun dossier `.kaggle`) |
| PyTorch + torchvision avec CUDA dans un environnement séparé | entraînement | à installer (ne pas l'ajouter aux dépendances de MedVision QA) |
| ~2 Go d'espace disque | données et poids | à vérifier |
| Ton accord pour l'usage (portfolio, non commercial) au vu des licences | toutes | à confirmer |

## 5. Ce qui n'est pas réutilisable du dépôt `brain-tumor-mri-classification`

Le notebook est vide, il n'y a ni poids ni prédictions versionnés, et l'évaluation ne
conserve que l'argmax, sans scores. Les chiffres du README ne sont donc pas
reproductibles ; il faut réentraîner. Le code `src/models.py` (SimpleCNN, ResNet18) reste
réutilisable.
