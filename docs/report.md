# Rapport HTML : Version Verification Record — v0.1

Implémentation : `src/medvision_qa/report.py`, gabarit
`src/medvision_qa/templates/report.html.j2`. Tests : `tests/test_report.py`.

```bash
python -m medvision_qa config.toml -o rapport.html
```

Code de sortie : `0` si le rapport est généré, quelle que soit la décision ; `2` si la
configuration ou les données sont invalides. Dans ce cas, aucun rapport n'est produit et
les erreurs sont affichées.

## 1. Propriétés garanties (testées)

| Propriété | Comment |
|---|---|
| 21 sections de la spécification (§ 10), dans l'ordre | `<h2 id="s1">` à `<h2 id="s21">` |
| Texte minimal de « What This Report Cannot Establish » | constante `CANNOT_ESTABLISH`, affichée intégralement |
| Aucune donnée inventée | tout vient de `EvaluationResult` ; un champ vide est affiché « Not provided » à sa place **et** récapitulé en section 19 |
| Nombres cohérents avec les calculs | IC, justifications, matrices de confusion, hashes comparés aux objets calculés |
| Autonome | CSS en ligne, aucun script, aucune URL externe, aucune police distante |
| Texte utilisateur échappé | titres, descriptions et justifications passent par l'échappement HTML de Jinja2 |
| Pas de chemin absolu | les fichiers sont affichés relativement à la configuration (pas de nom d'utilisateur ni d'arborescence locale) |
| Reproductible | même configuration → rapport identique, à l'identifiant et à l'horodatage d'exécution près |
| 4 états de taille d'échantillon | `Provided`, `Not provided`, `Not applicable`, `Based on data availability` (+ avertissement) ; taille réelle toujours affichée à part |

## 2. Contenu par section

| § | Section | Source |
|---|---|---|
| 1 | Identifiants | UUID d'exécution (identifie aussi le rapport), SHA-256 de la configuration |
| 2 | Date et heure | début d'exécution, UTC |
| 3 | Objectif | `evaluation.title`, `evaluation.objective`, type de comparaison, nombre de cas |
| 4 | Versions | `versions.*.id`, description, présence de scores |
| 5 | Code et poids | `code_commit`, `weights_sha256` **déclarés** (les poids ne sont pas lus) |
| 6 | Dataset | `data.description`, `data.nature`, `data.manifest_sha256` |
| 7 | Provenance | chemin relatif, SHA-256 **calculé** et nombre de lignes de chaque CSV |
| 8 | Prétraitement, dépendances | `versions.*.preprocessing`, graine, tolérance, Python, versions des paquets |
| 9 | Classes | ordre indexé, tâche binaire dérivée |
| 10 | Validation | mode de vérité terrain, alignement, contrôles exécutés par fichier |
| 11 | Métriques | estimation et IC par version, raisons d'indéfinition, avertissements, définitions |
| 12 | Matrices de confusion | une par version |
| 13 | Paramètres des IC | méthode, niveau, tirages, graine, unité et nombre d'unités |
| 14 | Tests statistiques | Δ = B − A apparié, McNemar (ou raison de non-applicabilité), statut de DeLong |
| 15 | Critères | définition de chaque critère, hash de la configuration |
| 16 | Décision | état et justification par critère, conclusion globale, règle d'agrégation |
| 17 | Taille d'échantillon | taille réelle, état, texte fourni, avertissement si applicable |
| 18 | Robustesse | « non exécutés » (non pris en charge en v0.1) |
| 19 | Non disponible | liste générée : métadonnées manquantes, métriques indéfinies, tests non applicables |
| 20 | Limites | liste générée selon les données (nature, `patient_id`, multiplicité...) et limites générales |
| 21 | What This Report Cannot Establish | texte fixe de la spécification |

## 3. Limites connues

- Rapport en français. Seuls les libellés imposés par la spécification sont en anglais
  (« What This Report Cannot Establish », « Not provided », états de décision).
- Pas de graphiques (courbes ROC, etc.) : uniquement des tableaux.
- Les métadonnées déclarées (commit, hash des poids, prétraitement) sont affichées telles
  quelles : l'outil ne peut pas vérifier qu'elles correspondent aux modèles réellement
  utilisés.
