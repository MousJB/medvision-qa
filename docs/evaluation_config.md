# Configuration d'évaluation, critères d'acceptation et métadonnées — v0.1

Statut : défini en Phase 0. Lecture/validation (`src/medvision_qa/config.py`) et moteur de
décision (`src/medvision_qa/decision_engine.py`) **implémentés en Phase 2**. L'affichage
des métadonnées dans le rapport arrive en Phase 3. L'exemple ci-dessous est chargé tel
quel par `tests/test_config.py`.

Chemins de fichiers : **relatifs au dossier du fichier de configuration**, sans en sortir.
Les chemins absolus et `..` sont refusés (protection contre la traversée de
répertoires). Le fichier doit exister.

Format : **TOML** (lisible, commentable, lu par `tomllib` de la bibliothèque standard,
sans dépendance). Clé inconnue → erreur, afin qu'une faute de frappe ne désactive pas
silencieusement un critère.

---

## 1. Exemple complet

```toml
schema_version = "0.1"

[evaluation]
title = "SimpleCNN v1 vs v2 — test standard"
objective = "Vérifier que v2 n'est pas inférieure à v1 sur la macro-F1."

[classes]
order = ["glioma", "meningioma", "notumor", "pituitary"]
positive = ["glioma", "meningioma", "pituitary"]   # optionnel ; tumeur vs notumor. Requis pour sensibilité/spécificité/AUROC

[data]
ground_truth_mode = "separate_file"   # ou "embedded"
ground_truth_file = "ground_truth.csv"
description = "Kaggle MRI-BT, dossier Testing/"
manifest_sha256 = ""          # vide = non fourni, affiché comme tel

[versions.A]
id = "simplecnn-v1"
predictions_file = "preds_v1.csv"
code_commit = ""              # vide = non fourni ; jamais deviné
weights_sha256 = ""
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
seed = 20261029               # obligatoire, pas de valeur par défaut
probability_sum_tolerance = 1e-3

[sample_size]
status = "not_provided"       # provided | not_provided | not_applicable | based_on_data_availability
justification = ""            # requis si provided ou not_applicable

[[criteria]]
id = "C1"
description = "Macro-F1 de B non inférieure à A, marge 0,02"
kind = "non_inferiority"
metric = "macro_f1"
margin = 0.02

[[criteria]]
id = "C2"
description = "Rappel glioma de B au moins 0,90"
kind = "absolute"
metric = "recall"
class = "glioma"
threshold = 0.90
```

---

## 2. Champs

### Valeurs non fournies

Un champ de métadonnées vide (`""`) signifie **non fourni**, et le rapport affiche
« Not provided ». L'outil ne calcule ni ne devine jamais un commit, un hash, un
identifiant de modèle ou une provenance qui n'a pas été fourni.

### `[statistics]`

| Champ | Règle |
|---|---|
| `confidence_level` | réel dans `]0, 1[` |
| `bootstrap_resamples` | entier ≥ 1000 (en dessous, les bornes percentiles sont trop instables) |
| `seed` | entier, **obligatoire** : sans graine, pas de reproductibilité |
| `probability_sum_tolerance` | réel > 0 |

### `[sample_size]` (section 9 de la spécification)

| `status` | `justification` | Affichage |
|---|---|---|
| `provided` | obligatoire (méthode, hypothèses, paramètres, référence) | texte fourni |
| `not_provided` | doit être vide | **Not provided** |
| `not_applicable` | obligatoire (raison) | texte fourni |
| `based_on_data_availability` | optionnelle | avertissement : *ce n'est pas une justification statistique* |

La taille réelle de l'échantillon est toujours affichée séparément.

---

## 3. Critères d'acceptation

### Métriques autorisées dans un critère (v0.1)

| `metric` | Paramètre | Nécessite |
|---|---|---|
| `accuracy` | — | — |
| `macro_f1` | — | — |
| `precision`, `recall`, `f1` | `class` | — |
| `sensitivity`, `specificity` | — | `classes.positive` (tâche binaire dérivée, voir [data_format.md](data_format.md#classes-positives-tâche-binaire-dérivée)) |
| `auroc` | — | `classes.positive` et des scores |

Comparaison d'AUROC entre versions : bootstrap apparié (Phase 2). DeLong n'est pas
implémenté en v0.1, faute de référence indépendante disponible pour le valider (R absent).

Toutes ces métriques sont « plus haut = mieux ».

### Types de critères et règles de décision

Toutes les décisions reposent sur l'**intervalle de confiance bilatéral** au niveau
`confidence_level` (bootstrap, Phase 1/2), jamais sur la seule estimation ponctuelle.
Notation : `[L, U]` = bornes de l'IC.

**`absolute`** — la métrique d'une version contre un seuil `threshold` ∈ [0, 1]. Clé
optionnelle `version = "A"` ou `"B"`. Par défaut : B si elle est déclarée, sinon A. La
version retenue est affichée dans le résultat.

| Condition | État |
|---|---|
| `L ≥ threshold` | `SATISFIED` |
| `U < threshold` | `NOT_SATISFIED` |
| sinon | `INCONCLUSIVE` |

**`non_inferiority`** — différence `Δ = B − A`, marge `margin > 0` :

| Condition | État |
|---|---|
| `L(Δ) > −margin` | `SATISFIED` |
| `U(Δ) < −margin` | `NOT_SATISFIED` |
| sinon | `INCONCLUSIVE` |

Avec un IC bilatéral à 95 %, cela correspond à un test unilatéral à α = 2,5 %. Une
absence de différence significative n'entraîne **jamais** `SATISFIED`.

**`superiority`** — différence `Δ = B − A` :

| Condition | État |
|---|---|
| `L(Δ) > 0` | `SATISFIED` |
| `U(Δ) ≤ 0` | `NOT_SATISFIED` |
| sinon | `INCONCLUSIVE` |

**Dans tous les cas**, le critère est `INCONCLUSIVE`, avec la raison, si la métrique est
indéfinie (par exemple, une classe absente), si les données requises manquent (pas de
scores pour l'AUROC), si l'IC n'est pas calculable, ou si l'IC est **de largeur nulle**
(voir [comparison.md § 3](comparison.md#3-moteur-de-décision)).

Les critères `non_inferiority` et `superiority` exigent `[versions.B]`. `margin` ∈ ]0, 1[.

### Agrégation globale

| Condition | État global |
|---|---|
| au moins un critère `NOT_SATISFIED` | `NOT_SATISFIED` |
| sinon, au moins un critère `INCONCLUSIVE` | `INCONCLUSIVE` |
| tous les critères `SATISFIED` | `SATISFIED` |
| aucun critère défini | erreur : une évaluation sans critère ne produit pas de décision |

Pas de moyenne ni de pondération : chaque critère reste visible individuellement.

---

## 4. Critères définis avant l'analyse : ce que l'outil peut et ne peut pas garantir

L'outil enregistre le hash SHA-256 du fichier de configuration et l'horodatage
d'exécution, puis les affiche dans le rapport. Il **ne peut pas prouver** que les
critères ont été écrits avant que les résultats soient connus. Pratique recommandée :
committer la configuration dans git avant la première exécution ; le rapport affichera
le hash, ce qui permet à un relecteur de le comparer au commit.
