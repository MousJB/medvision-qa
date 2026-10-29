# Protocole de l'expérience IRM figshare — fixé avant entraînement

Date : 2026-10-29. Ce document et `figshare_eval/config.toml` sont commités **avant**
le premier entraînement. Tout écart ultérieur sera signalé dans `README.md`.

## Données

- figshare « brain tumor dataset », Jun Cheng, v8, CC BY 4.0. Téléchargement vérifié par
  MD5 (`download_figshare.py`).
- 3 064 coupes, 233 patients, 3 classes : glioma, meningioma, pituitary. `case_id` =
  numéro du fichier `.mat` ; `patient_id` = `cjdata.PID`.

## Séparation

- **Par patient**, stratifiée par classe : chaque patient n'a qu'un type de tumeur. Si un
  patient apparaît avec plusieurs classes, l'anomalie est signalée et le patient est
  exclu, en le documentant.
- 60 % des patients pour l'entraînement, 10 % pour la validation, 30 % pour le test.
  Graine 20261029.
- Le jeu de test n'est utilisé qu'une fois, pour produire les prédictions finales. Aucun
  réglage n'est fait sur le test.

## Modèles (deux versions)

| Version | Modèle | Entraînement |
|---|---|---|
| A | SimpleCNN (architecture de `MousJB/brain-tumor-mri-classification`) | depuis zéro |
| B | ResNet18 torchvision pré-entraîné ImageNet | toutes les couches |

Recette commune : Adam (lr 1e-3 pour A, 1e-4 pour B), 15 époques au maximum, taille de
lot 32, perte d'entropie croisée, augmentation légère (retournement horizontal, rotation
± 10°). Le **checkpoint retenu est celui de meilleure macro-F1 de validation**. Graine
20261029, mode déterministe de cuDNN.

## Sorties

- `figshare_eval/ground_truth.csv` (`case_id`, `true_label`, `patient_id`).
- `figshare_eval/preds_*.csv` (`predicted_label` = argmax, `score_*` = softmax).
- SHA-256 des poids, configuration d'entraînement et versions des bibliothèques, dans
  `figshare_eval/training_*.json`.
- Rapport MedVision QA généré avec `figshare_eval/config.toml`.

## Critères d'acceptation

Voir `figshare_eval/config.toml` (C1 non-infériorité macro-F1, marge 0,03 ; C2 sensibilité
gliome ≥ 0,90 ; C3 supériorité de l'AUROC gliome).
