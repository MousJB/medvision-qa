# Comparaison de deux versions — v0.1

Implémentation : `src/medvision_qa/comparison.py`, `src/medvision_qa/decision_engine.py`,
`src/medvision_qa/evaluation.py`. Tests : `tests/test_comparison.py`,
`tests/test_decision_engine.py`, `tests/test_evaluation.py`.

Prérequis : les deux versions sont évaluées sur **exactement les mêmes cas** (vérifié par
l'alignement, voir [data_format.md](data_format.md#6-alignement-des-cas)).

## 1. Différences appariées par bootstrap

Pour chaque métrique de [metrics.md](metrics.md), Δ = B − A (positif = B meilleure).

- À chaque tirage, **les mêmes indices** de cas (ou de patients) servent pour A et pour B.
  C'est ce qui exploite l'appariement : la corrélation entre A et B réduit l'incertitude
  sur Δ. Un test montre un IC de Δ de largeur inférieure à 0,03 alors que chaque accuracy
  seule (≈ 0,75 sur 400 cas) a une incertitude d'environ ±0,04.
- Méthode, graine, unité et règles d'indéfinition sont celles de
  [metrics.md § 3](metrics.md#3-intervalles-de-confiance). Δ est indéfini dès que la
  métrique l'est pour A ou pour B.
- **AUROC** : la différence d'AUROC est estimée de cette façon. **DeLong n'est pas
  implémenté**, faute de référence indépendante (R/pROC) pour le valider. Ce statut est
  inscrit dans chaque résultat (`EvaluationResult.delong_status`).

## 2. Test de McNemar (informatif)

- Porte sur la **justesse** appariée : chaque cas est correct ou incorrect pour A et pour
  B. b = A seule correcte, c = B seule correcte.
- Variante **exacte conditionnelle** : test binomial bilatéral de b parmi b + c, p = ½
  (`scipy.stats.binomtest`). Elle a été vérifiée contre la formule fermée
  2·P(X ≤ min(b, c)), écrite à la main dans les tests. La variante exacte est choisie
  parce qu'elle reste valide avec peu de paires discordantes, contrairement à
  l'approximation χ².
- **Non applicable**, avec la raison, si :
  - plusieurs cas appartiennent au même patient : les paires ne sont pas indépendantes ;
  - aucune paire n'est discordante (b + c = 0).
- McNemar **n'entre pas dans les décisions** : celles-ci reposent sur les IC (§ 3). Une
  p-valeur élevée ne prouve ni l'équivalence ni l'absence de régression.

## 3. Moteur de décision

Règles : [evaluation_config.md § 3](evaluation_config.md#3-critères-dacceptation).
L'implémentation ajoute une règle de prudence :

- un **IC de largeur nulle** (métrique constante dans tous les tirages, par ex. accuracy =
  1, ou A et B identiques sur tous les cas) donne `INCONCLUSIVE`, jamais `SATISFIED`. Le
  bootstrap percentile ne mesure pas l'incertitude dans ce cas.

Chaque critère conserve son IC, la quantité comparée (par ex. `macro_f1 (B − A)`) et une
raison lisible (par ex. `IC [-0.0412, 0.0187] contient −marge (-0.0300) ; la non-infériorité n'est ni
démontrée ni exclue`).

## 4. Traçabilité d'une exécution

`run_evaluation(config)` enregistre : identifiant d'exécution (UUID4), horodatage UTC,
version de Python, versions de medvision-qa, numpy, scipy, scikit-learn et jinja2, SHA-256 de la
configuration et de chaque CSV, contrôles exécutés par fichier, paramètres du bootstrap,
matrices de confusion.

Deux exécutions de la même configuration donnent des intervalles et des décisions
identiques (testé). Seuls l'identifiant et l'horodatage changent.

## 5. Limites

- Δ est une différence absolue de métrique. Pas de rapport de cotes ni de différence
  relative.
- Le bootstrap apparié hérite des limites du bootstrap percentile (petits échantillons,
  métriques proches des bornes).
- Les critères sont évalués indépendamment, sans correction de multiplicité. La règle
  d'agrégation (tous `SATISFIED` pour un `SATISFIED` global) est conservatrice, mais avec
  beaucoup de critères la probabilité d'un `NOT_SATISFIED` dû au hasard augmente.
- L'outil ne peut pas prouver que les critères ont été fixés avant l'analyse (voir
  [evaluation_config.md § 4](evaluation_config.md#4-critères-définis-avant-lanalyse--ce-que-loutil-peut-et-ne-peut-pas-garantir)).
