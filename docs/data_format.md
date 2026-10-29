# Format des fichiers d'entrée — v0.1

Statut : **défini en Phase 0, pas encore implémenté.** La Phase 1 implémente ces règles et
les tests associés. Toute règle modifiée en Phase 1 doit être mise à jour ici.

Principe général : **toute violation est une erreur bloquante.** Aucune ligne n'est
supprimée, aucune valeur n'est corrigée, normalisée ou remplacée silencieusement.

---

## 1. Règles communes à tous les CSV

| Règle | Comportement |
|---|---|
| Encodage | UTF-8, avec ou sans BOM (Excel ajoute un BOM). Autre encodage → erreur. |
| Séparateur | Virgule `,`. Guillemets selon RFC 4180. |
| En-tête | Obligatoire, première ligne. |
| Noms de colonnes dupliqués | Erreur. |
| Colonnes inconnues | Erreur, sauf si elles commencent par `meta_` (conservées, jamais utilisées dans les calculs). |
| Ligne vide ou nombre de champs incorrect | Erreur avec numéro de ligne. |
| Espaces en début/fin de valeur | Erreur (pas de `strip()` silencieux). |
| Fichier sans ligne de données | Erreur. |

Chaque erreur indique : fichier, numéro de ligne (1 = en-tête), colonne, valeur fautive,
règle violée.

---

## 2. Classes

Les classes sont déclarées dans la configuration d'évaluation
([evaluation_config.md](evaluation_config.md)), **pas déduites des données**.

- Liste ordonnée, au moins 2 classes, sans doublon.
- Noms : `^[A-Za-z0-9_-]+$`, sensibles à la casse (`Glioma` ≠ `glioma`).
- L'ordre déclaré fixe l'ordre des lignes/colonnes de la matrice de confusion et
  l'ordre attendu des colonnes de scores.
- Une classe déclarée peut être absente des données : ce n'est pas une erreur de
  format, mais les métriques qui en dépendent seront marquées **indéfinies** (Phase 1).

Exemple pour le dataset IRM : `["glioma", "meningioma", "notumor", "pituitary"]`.

### Classes positives (tâche binaire dérivée)

`positive` est une liste non vide de classes déclarées, différente de l'ensemble complet
des classes. Elle définit une tâche binaire « positives contre les autres » :

- vérité binaire : `true_label ∈ positive` ;
- prédiction binaire : `predicted_label ∈ positive` (décision multiclasse existante,
  sans nouveau seuil) ;
- score binaire : somme des `score_<classe>` des classes positives (utilisé pour
  l'AUROC uniquement).

Exemple IRM, tumeur contre pas de tumeur : `positive = ["glioma", "meningioma", "pituitary"]`.
Un contre tous : `positive = ["glioma"]`.

---

## 3. Fichier de vérité terrain (`ground_truth.csv`)

Source unique des labels de référence, partagée par les versions A et B.

| Colonne | Obligatoire | Type | Règles |
|---|---|---|---|
| `case_id` | oui | texte | non vide, unique dans le fichier |
| `true_label` | oui | texte | doit appartenir aux classes déclarées |
| `patient_id` | non | texte | non vide si la colonne existe ; plusieurs cas peuvent partager un patient |
| `meta_*` | non | texte | ignoré par les calculs |

Sans `patient_id`, toute inférence est **au niveau image/cas**, et le rapport le dira.
Avec `patient_id`, la Phase 1 pourra rééchantillonner par patient (bootstrap par grappes).

```csv
case_id,true_label,patient_id
img_0001,glioma,P001
img_0002,notumor,P002
```

---

## 4. Fichier de prédictions (un par version)

| Colonne | Obligatoire | Type | Règles |
|---|---|---|---|
| `case_id` | oui | texte | non vide, unique dans le fichier |
| `predicted_label` | oui | texte | doit appartenir aux classes déclarées |
| `score_<classe>` | non, mais **tout ou rien** | réel | une colonne par classe déclarée, aucune en plus |
| `true_label` | non | texte | voir § 5 |
| `meta_*` | non | texte | ignoré par les calculs |

### Règles sur les scores

Si au moins une colonne `score_*` est présente :

1. il doit y en avoir exactement une par classe déclarée (ni manquante, ni en trop) ;
2. chaque valeur est un réel fini dans `[0, 1]` (`nan`, `inf`, vide → erreur) ;
3. la somme par ligne vaut 1 à une tolérance près (défaut `1e-3`, configurable et
   reportée dans le rapport) — les scores doivent donc être des sorties de type softmax ;
4. `predicted_label` doit être une des classes de score maximal (argmax ; en cas
   d'égalité, n'importe laquelle des classes ex æquo est acceptée). Une incohérence est
   une erreur. La v0.1 ne prend pas en charge les règles de décision par seuil.

Sans scores, les métriques fondées sur les scores (AUROC) seront **indisponibles**, pas
estimées.

```csv
case_id,predicted_label,score_glioma,score_meningioma,score_notumor,score_pituitary
img_0001,glioma,0.91,0.05,0.02,0.02
img_0002,notumor,0.03,0.10,0.80,0.07
```

---

## 5. Où se trouvent les vérités terrain

Deux modes, exclusifs et explicites dans la configuration :

- **Mode `separate_file` (recommandé)** : un `ground_truth.csv`. Si un fichier de
  prédictions contient aussi `true_label`, chaque valeur doit être identique à celle du
  fichier de vérité terrain, sinon erreur.
- **Mode `embedded`** : pas de fichier séparé ; chaque fichier de prédictions contient
  `true_label`. En comparaison A/B, `true_label` doit être identique dans A et B pour
  chaque `case_id`, sinon erreur. `patient_id` n'est pas disponible dans ce mode.

---

## 6. Alignement des cas

- L'alignement se fait **uniquement par `case_id`**, en égalité exacte de chaîne.
  L'ordre des lignes n'a aucune importance.
- Deux fichiers ne sont jamais appariés par position ou par nombre de lignes.
- Les ensembles de `case_id` de la vérité terrain, de A et de B doivent être
  **identiques**. Tout cas manquant ou en trop → erreur, avec la liste des identifiants
  concernés (tronquée à l'affichage, complète dans le journal de validation).
- Il n'existe pas de mode « intersection » qui écarterait les cas non communs. Si une
  sous-sélection est nécessaire, elle doit être faite en amont, et documentée.

---

## 7. Limites connues du format v0.1

- Classification mono-label uniquement (pas de multi-label, pas de segmentation).
- Pas de scores binaires à une seule colonne : en binaire, fournir les deux colonnes.
- Le format ne peut pas vérifier que les `case_id` désignent réellement les mêmes images
  pour A et B ; il vérifie seulement la cohérence des identifiants. Le hash du manifeste
  de données (Phase 3) sert à tracer ce point.
