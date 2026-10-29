# Phase 0 — Inspection et cadrage

Date : 2026-10-29

## 1. Environnement local

| Élément | Constat |
|---|---|
| OS | Windows 10 Home 10.0.19045 |
| Python | 3.12.6 (`C:\Python312`) ; environnement virtuel `.venv/` du projet |
| Dépendances installées | numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, pytest 9.2.0. Versions exactes dans `requirements-lock.txt` |
| git | 2.44.0 ; dépôt initialisé sur `main`, aucun commit à ce stade |
| R / pROC | **absent** : pas de validation indépendante de DeLong pour l'instant (voir § 4) |
| GPU | CUDA 12.3 présent dans le PATH ; non vérifié et non nécessaire avant la Phase 4 |

## 2. Dépôt candidat : `MousJB/brain-tumor-mri-classification`

Inspecté via l'API GitHub (lecture seule, aucun clonage, aucune donnée téléchargée).

| Élément | Constat |
|---|---|
| Licence du code | MIT |
| Contenu | `src/dataset.py`, `src/models.py`, `src/utils.py`, `README.md`, `requirements.txt` |
| Notebook | `notebooks/Brain_Tumor_Classification.ipynb` est **vide** (2 octets) |
| Checkpoints / prédictions | **aucun** dans le dépôt |
| Classes | glioma, meningioma, no-tumor, pituitary. L'ordre des indices dépend de la liste `classes` passée au `Dataset`, qui n'est pas fixée dans le code versionné |

### Conséquences

- Les résultats du README (94,58 %, 98,09 %, etc.) **ne sont pas reproductibles depuis le
  dépôt** : le notebook qui les a produits est vide et aucun poids n'est versionné. Ils ne
  doivent pas être repris comme résultats de référence par MedVision QA.
- Le README parle de « validation accuracy » alors que le dataset n'a que des dossiers
  `Training/` et `Testing/`. L'origine du jeu de validation n'est pas documentée. À
  éclaircir avant toute réutilisation (Phase 4).
- `evaluate_model` ne conserve que l'argmax : il ne produit **pas de scores**. Pour
  l'AUROC, il faudra exporter les probabilités softmax au format défini dans
  [data_format.md](data_format.md).
- Observation sur le prétraitement, à vérifier en Phase 4 et non corrigée ici : après une
  standardisation z-score, l'image est encore divisée par 255, ce qui semble
  involontaire.

## 3. Dataset : Kaggle « MRI Brain Tumor Dataset: 4-Class (7,023 Images) »

Métadonnées lues via l'API publique Kaggle
(`mohamadabouali1/mri-brain-tumor-dataset-4-class-7023-images`, version 1).

| Élément | Constat |
|---|---|
| Licence déclarée sur Kaggle | MIT |
| Auteur | Mohamad Abou Ali |
| Taille | ~139 Mo |
| Jeux « Blurred », « Noisy », « Patient Motion Artifact » | décrits par l'auteur comme **synthétiques** |

### Points non vérifiés

- **Provenance amont des images** : la description Kaggle ne précise pas l'origine des
  7 023 images. Si elles proviennent de jeux publics antérieurs, la licence MIT déclarée
  ne garantit pas les droits d'origine. À vérifier, par exemple sur le dépôt GitHub
  cité par l'auteur et dans ses articles, avant toute démonstration publique.
- Doublons exacts et quasi-doublons entre `Training/` et `Testing/` : non examinés
  (Phase 4).
- Absence d'identifiant patient : probable, à confirmer. Sans `patient_id`, toute
  inférence restera au niveau image.

### Conséquence pour le rapport

Les résultats sur Blurred, Noisy et Motion devront être présentés comme des **tests de
sensibilité sur données synthétiques**, pas comme une validation en conditions réelles
d'acquisition.

## 4. DeLong

R n'est pas installé. Selon la section 7 de la spécification, cela ne bloque pas la
Phase 1. Décision (§ 6) : bootstrap apparié en Phase 2, DeLong marqué « non implémenté ».

## 5. Décisions de Phase 0

| Sujet | Décision |
|---|---|
| Format des entrées | [data_format.md](data_format.md) : vérité terrain séparée (recommandé), un CSV de prédictions par version, alignement strict par `case_id` |
| Configuration et critères | [evaluation_config.md](evaluation_config.md) : TOML, critères décidés sur IC, agrégation sans moyenne |
| Arborescence | `src/medvision_qa/` (package installable) au lieu de `app/` (spec § 11, indicative) : nom non générique, imports identiques en tests et en production. Modules créés phase par phase, aucun module vide |
| Dépendances | uniquement ce qu'utilisent les phases 1 et 2 (numpy, scipy, scikit-learn) ; FastAPI, Jinja2 et SQLite seront ajoutés en Phase 3/5 |
| Lecture CSV | prévue avec le module standard `csv` plutôt que pandas, pour éviter les conversions implicites (`"NA"` → NaN, inférence de types). À confirmer en Phase 1 |

## 6. Questions tranchées en fin de Phase 0

| Question | Décision | Raison |
|---|---|---|
| Licence | MIT (`LICENSE`) | cohérente avec le dépôt IRM ; simple pour un portfolio |
| Classe positive | `positive` = **liste** de classes ; démo IRM : tumeur (`glioma`, `meningioma`, `pituitary`) contre `notumor` | question clinique la plus naturelle pour ce dataset ; le un-contre-tous reste possible avec une liste d'une seule classe |
| Règle de décision par seuil | non prise en charge en v0.1 : `predicted_label` doit être l'argmax | moins de cas ambigus ; ajout possible plus tard si un besoin réel apparaît |
| DeLong | non implémenté ; comparaison d'AUROC par bootstrap apparié en Phase 2 | aucune référence indépendante disponible (R absent) ; pas de méthode non validée exposée |

Reste ouvert : le dossier s'appelle toujours `projet IA`. Le renommer en `medvision-qa`
quand VS Code est fermé.

## 7. Gate de Phase 0

| Condition | État |
|---|---|
| Schéma et périmètre documentés | fait : `docs/data_format.md`, `docs/evaluation_config.md` |
| Environnement reproductible | `.venv` + `pyproject.toml` + `requirements-lock.txt` |
| Tests de base exécutables | `pytest` : 3 passed (2026-10-29) |
| Licences et droits des données | licence déclarée identifiée ; **provenance amont non vérifiée**. Ce point ne bloque pas les phases 1 à 3, qui utilisent des fixtures synthétiques, mais bloque la Phase 4 |
