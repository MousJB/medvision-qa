# Métriques et intervalles de confiance — v0.1

Implémentation : `src/medvision_qa/metrics.py`, `src/medvision_qa/confidence_intervals.py`.
Validées contre scikit-learn (référence indépendante) dans `tests/test_metrics.py`.

## 1. Conventions

- Matrice de confusion : lignes = vérité, colonnes = prédiction, dans l'ordre de
  `classes.order`.
- Les métriques par classe sont en **un contre tous**. TP, FP et FN sont lus dans la
  matrice de confusion.
- Une métrique non calculable est **indéfinie, avec une raison**. Elle n'est jamais
  remplacée par 0, par NaN ou par une autre valeur.
- Clé d'une métrique : `accuracy`, `macro_f1`, `precision[<classe>]`, `recall[<classe>]`,
  `f1[<classe>]`, `sensitivity`, `specificity`, `auroc`.

## 2. Définitions et cas indéfinis

| Métrique | Définition | Indéfinie si |
|---|---|---|
| `accuracy` | cas corrects / cas | jamais (fichier non vide garanti) |
| `precision[c]` | TP / (TP + FP) | `c` n'est jamais prédite |
| `recall[c]` | TP / (TP + FN) | `c` est absente des vérités terrain |
| `f1[c]` | 2·TP / (2·TP + FP + FN) | `c` est absente des vérités terrain **et** des prédictions |
| `macro_f1` | moyenne non pondérée des `f1[c]` sur **toutes** les classes déclarées | un `f1[c]` est indéfini (aucune classe n'est écartée en silence) |
| `sensitivity` | TP / (TP + FN), tâche binaire dérivée | pas de classe positive, ou aucun cas positif |
| `specificity` | TN / (TN + FP), tâche binaire dérivée | pas de classe positive, ou aucun cas négatif |
| `auroc` | Mann-Whitney sur le score positif ; ex æquo comptés ½ | pas de classe positive, pas de scores, ou une seule classe binaire présente |

Note sur `f1[c]` : la formule 2·TP / (2·TP + FP + FN) vaut 0 quand la classe est présente
mais jamais correctement prédite, même si la précision est indéfinie. C'est le même
résultat que scikit-learn avec `zero_division`, testé.

Tâche binaire dérivée (voir [data_format.md](data_format.md#classes-positives-tâche-binaire-dérivée)) :
la prédiction binaire vient de `predicted_label` (aucun nouveau seuil), et le score
positif est la somme des scores des classes positives.

## 3. Intervalles de confiance

| Paramètre | Valeur |
|---|---|
| Méthode | bootstrap **percentile**, bilatéral |
| Quantiles | `numpy.quantile(..., method="linear")` |
| Rééchantillonnages | ≥ 1000 (paramètre `bootstrap_resamples`) |
| Graine | obligatoire ; générateur `numpy.random.default_rng(seed)` |
| Unité | **patient** si `patient_id` est fourni (tous les cas d'un patient tiré sont inclus), sinon **cas** |
| Ordre des cas | trié par `case_id` : le résultat ne dépend pas de l'ordre des lignes des fichiers |

Tous ces paramètres sont enregistrés dans `BootstrapSettings`.

### Quand aucun intervalle n'est produit

- La métrique est indéfinie sur l'échantillon complet.
- La métrique est indéfinie dans **au moins un** rééchantillonnage, par exemple une classe
  rare absente d'un tirage. Écarter ces tirages conditionnerait l'intervalle et le
  rendrait trop optimiste. L'intervalle est donc déclaré non calculable, avec le nombre
  de tirages concernés.

### Avertissements attachés à un intervalle

- **Largeur nulle** : la métrique est constante dans tous les tirages (par ex. accuracy =
  1). Le bootstrap percentile ne reflète alors pas l'incertitude réelle.
- **Moins de 30 unités** de rééchantillonnage : la couverture du bootstrap percentile
  n'est pas garantie. Le seuil de 30 est une convention, pas une garantie.

## 4. Limites

- Sans `patient_id`, l'intervalle suppose des cas indépendants. Si plusieurs images
  viennent du même patient, il sera **trop étroit** (`tests/test_confidence_intervals.py`
  montre un écart de plus de ×2 sur un exemple synthétique).
- Le bootstrap percentile peut avoir une couverture inférieure au niveau nominal pour
  les petits échantillons ou les métriques proches de 0 ou 1. Les méthodes BCa ou Wilson
  ne sont pas implémentées en v0.1.
- Un intervalle large n'est pas une preuve d'absence de différence. Les comparaisons
  entre versions (bootstrap apparié) et les décisions arrivent en Phase 2.
- Pas de macro-AUROC multiclasse en v0.1 : seule l'AUROC de la tâche binaire dérivée est
  calculée.
