# MedVision QA — Spécification complète du projet

**Version :** 1.0  
**Date de référence :** 29 octobre 2026  
**Durée cible du MVP :** 30 jours  
**Statut :** spécification de travail — certains choix techniques restent à valider.

---

## 1. Résumé exécutif

**MedVision QA** est un outil de vérification, de comparaison et de documentation technique des versions de modèles de classification d’images médicales.

À partir de prédictions produites par deux versions d’un modèle, l’application valide les données, calcule des métriques pertinentes, quantifie l’incertitude, compare les performances sur les mêmes cas, applique des critères d’acceptation définis à l’avance et génère un **Version Verification Record** au format HTML.

L’objectif est de rendre les évaluations de versions plus reproductibles, traçables et faciles à examiner par une équipe technique ou qualité.

MedVision QA est un **outil d’aide à l’évaluation technique**, pas un dispositif médical, un outil de diagnostic, une validation clinique, une certification réglementaire ou une preuve de conformité.

### Proposition de valeur

Un workflow simple et intégré pour :

1. vérifier la qualité des fichiers de prédictions ;
2. calculer des métriques définies et documentées ;
3. comparer deux versions évaluées sur les mêmes cas ;
4. appliquer des critères d’acceptation préétablis ;
5. conserver les paramètres et les limites de l’analyse ;
6. produire un rapport HTML autonome, reproductible et compréhensible.

### Hypothèse de différenciation

La différenciation à tester n’est pas « il n’existe aucun outil concurrent ». Des outils de suivi d’expériences, bibliothèques d’imagerie médicale et plateformes de recherche existent déjà. L’hypothèse est que certains utilisateurs apprécieraient un workflow compact réunissant validation des entrées, comparaison statistique, critères d’acceptation explicites et rapport de vérification versionné.

Cette hypothèse doit être validée auprès d’utilisateurs réels.

---

## 2. Contexte et problème

Les équipes qui développent des modèles d’imagerie médicale peuvent devoir comparer une nouvelle version à une version de référence, documenter les résultats et expliquer si des critères techniques prédéfinis sont satisfaits.

Un simple score d’accuracy ne suffit pas toujours. Une comparaison sérieuse peut nécessiter :

- des métriques par classe ;
- une matrice de confusion ;
- des intervalles de confiance ;
- une comparaison appariée lorsque les deux versions ont été évaluées sur les mêmes cas ;
- une vérification des fichiers d’entrée et de l’identité des cas ;
- des critères d’acceptation définis avant l’analyse ;
- des métadonnées permettant de reproduire ou d’auditer l’analyse ;
- une explication explicite de ce que les résultats ne permettent pas de conclure.

Le projet vise à rendre ces étapes moins dispersées et à réduire les erreurs de traitement ou les conclusions excessives.

### Utilisateurs cibles à explorer

- ingénieurs Machine Learning travaillant sur l’imagerie médicale ;
- chercheurs en IA médicale ;
- équipes de vérification et de validation technique ;
- responsables qualité travaillant avec des équipes de développement ;
- petites équipes qui ont besoin d’un rapport reproductible sans déployer une plateforme complète.

Ces profils sont des hypothèses de départ, pas des segments de marché déjà validés.

---

## 3. Objectifs

### Objectifs techniques

- Construire un outil Python fonctionnel et testable.
- Valider strictement les fichiers de prédictions.
- Calculer des métriques standard avec une définition explicite.
- Comparer deux versions sur les mêmes cas.
- Quantifier l’incertitude lorsque la méthode est applicable.
- Appliquer des critères d’acceptation prédéfinis sans les inventer.
- Générer un rapport HTML autonome avec résultats, métadonnées et limites.
- Conserver une trace des configurations et des artefacts utilisés.
- Démontrer le workflow sur un exemple d’imagerie médicale, si les données et les droits d’utilisation le permettent.

### Compétences démontrées

Le projet doit démontrer :

- Python et bonnes pratiques de développement ;
- traitement et validation de données ;
- évaluation de modèles de classification ;
- statistiques appliquées et incertitude ;
- compréhension des spécificités de l’imagerie médicale ;
- tests automatisés ;
- reproductibilité et traçabilité ;
- capacité à expliquer les limites scientifiques d’un résultat.

Il ne doit jamais être présenté comme un produit certifié ou cliniquement validé.

---

## 4. Non-objectifs et limites de portée

Le MVP ne cherchera pas à :

- diagnostiquer un patient ;
- prendre une décision clinique ;
- certifier un modèle médical ;
- démontrer une sécurité clinique ;
- certifier la conformité à ISO 13485, au FDA QMSR ou à une autre réglementation ;
- remplacer une validation clinique, un système qualité ou une revue humaine ;
- garantir l’absence de biais, de fuite de données ou de régression ;
- héberger des données médicales dans un service cloud multi-tenant ;
- fournir une authentification multi-utilisateur ;
- exécuter du code arbitraire fourni par les utilisateurs ;
- télécharger automatiquement des datasets soumis à des restrictions ;
- entraîner obligatoirement un nouveau modèle si les données, le temps ou le matériel ne le permettent pas ;
- intégrer un grand frontend Next.js dans le MVP sans besoin utilisateur établi.

Le rapport constitue une documentation technique de l’analyse réalisée. Il ne constitue pas, à lui seul, une preuve de conformité réglementaire.

---

## 5. Fonctionnement attendu

### Entrées

L’utilisateur fournit :

- un fichier de prédictions de référence (version A) ;
- un fichier de prédictions de la nouvelle version (version B), pour les comparaisons ;
- les vérités terrain associées, si elles ne figurent pas déjà dans les fichiers ;
- la définition des classes et leur ordre ;
- les métadonnées disponibles sur les versions ;
- les critères d’acceptation définis avant l’analyse ;
- les informations de protocole et de justification de taille d’échantillon, lorsqu’elles existent.

### Workflow

1. L’utilisateur crée une évaluation et renseigne les métadonnées.
2. L’application vérifie le schéma et la cohérence des fichiers.
3. Les cas et les labels sont alignés selon des identifiants explicites.
4. L’application refuse les entrées invalides au lieu de supprimer silencieusement des lignes.
5. Les métriques sont calculées avec leurs définitions et paramètres.
6. Les intervalles de confiance et tests statistiques sont calculés uniquement si les conditions d’application sont satisfaites.
7. Les versions sont comparées sur les mêmes cas lorsque la comparaison est appariée.
8. Les résultats sont confrontés aux critères d’acceptation préétablis.
9. L’application produit une conclusion parmi les états autorisés et explique son raisonnement.
10. Un rapport HTML autonome est généré avec les résultats, métadonnées, limites et avertissements.

### Sorties

- résultats de métriques ;
- matrices de confusion ;
- intervalles de confiance, si calculables ;
- résultats de comparaison statistique, si applicables ;
- état de chaque critère ;
- décision globale justifiée ;
- journal des validations et erreurs ;
- rapport HTML autonome ;
- métadonnées nécessaires pour comprendre et reproduire l’analyse.

---

## 6. Validation stricte des données

La validation des entrées est une fonctionnalité centrale, pas une étape accessoire.

### Vérifications requises

- colonnes requises présentes ;
- identifiants de cas non vides ;
- absence de doublons non autorisés ;
- absence de valeurs manquantes dans les champs obligatoires ;
- labels présents dans la liste des classes autorisées ;
- prédictions et vérités terrain cohérentes ;
- scores et probabilités numériques, finis et dans les bornes attendues ;
- somme des probabilités cohérente avec 1 dans une tolérance documentée, lorsque des probabilités multiclasses sont attendues ;
- ordre des classes explicite et cohérent ;
- absence de cas manquants ou supplémentaires dans une comparaison appariée ;
- cohérence des formats et des types ;
- identification des lignes ou champs à l’origine de chaque erreur.

### Comportement en cas d’erreur

- Ne jamais supprimer silencieusement des lignes.
- Ne jamais remplacer une valeur invalide par une valeur par défaut sans accord explicite et traçable.
- Bloquer les calculs affectés lorsque les données ne satisfont pas les exigences.
- Présenter des messages d’erreur actionnables.
- Conserver un résumé des contrôles exécutés.

Les règles d’alignement des cas doivent être explicites. Deux fichiers ne sont pas appariés simplement parce qu’ils contiennent le même nombre de lignes.

---

## 7. Métriques et méthodes statistiques

Les méthodes doivent être implémentées avec des tests et des définitions explicites. Les métriques non applicables ne doivent pas être remplacées par des valeurs inventées.

### Métriques de classification

Selon la tâche et les données disponibles :

- accuracy ;
- précision par classe ;
- rappel par classe ;
- F1-score par classe ;
- macro-F1 ;
- matrice de confusion ;
- sensibilité et spécificité lorsque leur définition est appropriée et que la classe positive est explicitement définie ;
- AUROC lorsque des scores continus adaptés sont disponibles et que la structure de la tâche permet ce calcul.

Le rapport doit préciser la classe positive, la stratégie d’agrégation, l’ordre des classes et la définition de chaque métrique.

Pour les cas où une métrique n’est pas calculable — par exemple, classe absente dans les vérités terrain — l’application doit utiliser un état documenté ou signaler que la métrique est indéfinie. Elle ne doit pas masquer le problème.

### Intervalles de confiance

- Utiliser un bootstrap adapté au type de donnée et à la métrique.
- Enregistrer le nombre de rééchantillonnages, la méthode, la graine et l’unité de rééchantillonnage.
- Décrire les hypothèses et limites.
- Ne pas prétendre faire une inférence au niveau patient si les identifiants de patient ou la structure de regroupement ne sont pas disponibles.
- Ne pas confondre un intervalle de confiance large avec une preuve d’absence de différence.

### Comparaison de deux versions

Les versions doivent être évaluées sur les mêmes cas pour les comparaisons appariées.

- McNemar : uniquement pour une comparaison appariée de résultats catégoriels binaires, avec les conditions et variantes de test documentées.
- AUROC : DeLong apparié lorsque les conditions sont satisfaites et l’implémentation validée ; sinon, envisager un bootstrap apparié correctement conçu.
- Autres métriques : utiliser une méthode adaptée à la métrique, à la structure appariée et aux hypothèses.
- Ne pas sélectionner un test statistique uniquement parce qu’il est facile à implémenter.
- Documenter les hypothèses, les limites et les raisons pour lesquelles une méthode est ou n’est pas disponible.

#### Validation indépendante de DeLong

R et `pROC::roc.test` peuvent servir de référence de validation indépendante, mais R ne doit pas devenir une dépendance d’exécution du produit.

Si R est indisponible :

1. ne pas bloquer les phases précédentes ;
2. chercher des résultats de référence fiables et indépendamment vérifiés, avec provenance documentée ;
3. si une validation indépendante suffisante n’est pas possible, ne pas prétendre que l’implémentation DeLong est validée ;
4. utiliser une méthode alternative correctement testée, telle qu’un bootstrap apparié, ou marquer la comparaison comme indisponible.

Ne jamais inventer de résultats de référence.

### Interprétation

- Un résultat non significatif ne prouve pas l’équivalence.
- Une différence non significative ne prouve pas l’absence de régression.
- Une amélioration moyenne n’implique pas une amélioration pour chaque classe ou sous-groupe.
- Une métrique seule ne prouve pas une utilité clinique.
- Une conclusion doit être limitée au protocole, aux données et aux méthodes réellement utilisés.

---

## 8. Critères d’acceptation et moteur de décision

Les critères doivent être définis **avant** l’analyse. L’application ne doit pas choisir automatiquement des seuils après avoir observé les résultats.

### États par critère

- `SATISFIED` : les éléments requis pour le critère sont présents et le critère prédéfini est satisfait.
- `NOT_SATISFIED` : les éléments requis sont disponibles et le critère prédéfini n’est pas satisfait.
- `INCONCLUSIVE` : les données, la précision, les hypothèses ou les méthodes disponibles ne permettent pas de trancher.

L’état global doit expliquer les règles d’agrégation entre critères. Il ne doit pas masquer un critère non satisfait ou inconclusif derrière une moyenne générale.

### Non-infériorité

Une analyse de non-infériorité nécessite notamment :

- une marge de non-infériorité définie à l’avance ;
- une métrique et une direction d’effet définies ;
- une méthode statistique adaptée ;
- un intervalle de confiance et une règle de décision cohérents avec le protocole.

Ne jamais conclure à la non-infériorité simplement parce qu’aucune différence statistiquement significative n’a été observée.

---

## 9. Justification de la taille d’échantillon

L’application doit distinguer le nombre de cas réellement évalués de la justification de la taille d’échantillon.

### États autorisés

1. **`Provided`** : l’utilisateur a fourni une justification, une méthode, les hypothèses, les paramètres et, si applicable, une référence.
2. **`Not provided`** : aucune justification n’a été fournie. Afficher exactement : **“Not provided”**.
3. **`Not applicable`** : l’utilisateur a explicitement choisi cet état et donné une raison.
4. **`Based on data availability`** : l’utilisateur déclare que le nombre de cas est dicté par la disponibilité des données. Afficher un avertissement indiquant que cela ne constitue pas une justification statistique.

### Règles

- Ne pas créer automatiquement de justification.
- Ne pas considérer le nombre de cas disponible comme une justification statistique.
- Ne pas déduire une puissance statistique sans hypothèses explicites.
- Enregistrer le texte fourni, l’état sélectionné et la date.
- Présenter distinctement la taille réelle de l’échantillon et l’état de justification.

---

## 10. Rapport HTML : Version Verification Record

Le rapport est le livrable central du projet. Il doit être autonome, lisible et suffisamment documenté pour permettre à une autre personne de comprendre ce qui a été exécuté.

### Sections obligatoires

1. Identifiant du rapport et de l’exécution.
2. Date et heure de l’évaluation.
3. Objectif et description de la comparaison.
4. Identifiants des versions comparées.
5. Informations disponibles sur le code, le commit, les poids et leurs hashes.
6. Manifeste du dataset et hash SHA-256, lorsque disponible.
7. Provenance des fichiers et statut des informations non fournies.
8. Prétraitement, configuration, dépendances et graines.
9. Définition des classes et ordre des classes.
10. Résumé des validations de données.
11. Métriques et définitions.
12. Matrices de confusion.
13. Intervalles de confiance et paramètres.
14. Tests statistiques, hypothèses et limites.
15. Critères d’acceptation définis avant l’analyse.
16. État de chaque critère et conclusion globale motivée.
17. Justification de taille d’échantillon et son état.
18. Résultats des tests de robustesse, le cas échéant.
19. Éléments non disponibles ou non exécutés.
20. Limites de l’analyse.
21. Section obligatoire **“What This Report Cannot Establish”**.

### Texte minimal pour “What This Report Cannot Establish”

Le rapport doit préciser au minimum :

- Un résultat non significatif ne prouve pas l’absence de régression, l’équivalence ou la non-infériorité.
- Cette analyse n’est pas une validation clinique ni une démonstration de sécurité clinique.
- Ce rapport ne certifie pas la conformité à ISO 13485, au FDA QMSR ou à une autre réglementation.
- Des tests de sensibilité synthétiques ne valident pas les conditions réelles d’acquisition clinique.
- La détection de quasi-doublons ne prouve pas à elle seule une fuite de données ni l’identité d’un patient.
- Les conclusions sont limitées aux données, au protocole, aux hypothèses et aux méthodes effectivement utilisés.

### Traçabilité et intégrité

Lorsque les éléments sont disponibles, enregistrer :

- hash du manifeste de données ;
- identifiants et hashes des artefacts ;
- version du code et commit ;
- versions des dépendances ;
- configuration et graines ;
- paramètres des métriques et méthodes statistiques ;
- statut des validations ;
- horodatage et identifiant d’exécution.

Une information indisponible doit être explicitement marquée comme indisponible. Ne pas inventer un commit, un hash, un identifiant de modèle ou une provenance.

---

## 11. Architecture technique

### Stack MVP

- **Python** : logique métier, validation, métriques et statistiques.
- **FastAPI** : routes et gestion des requêtes.
- **Jinja2** : rendu des pages HTML.
- **SQLite** : historique local des évaluations et métadonnées.
- **NumPy / SciPy / scikit-learn** : calculs numériques et métriques, selon les besoins vérifiés.
- **pytest** : tests automatisés.
- **R + pROC** : outil optionnel de validation indépendante de DeLong, pas une dépendance d’exécution.
- **HTML autonome** : rapport exportable et consultable sans frontend lourd.

### Pourquoi ne pas utiliser Next.js dans le MVP ?

Un frontend Next.js augmenterait la surface de développement sans bénéfice utilisateur démontré à ce stade. FastAPI et Jinja2 suffisent pour une première interface fonctionnelle. Une interface plus élaborée pourra être ajoutée si les retours utilisateurs le justifient.

### Structure indicative

```text
medvision-qa/
├── app/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   │   ├── validation.py
│   │   ├── metrics.py
│   │   ├── confidence_intervals.py
│   │   ├── comparison.py
│   │   ├── decision_engine.py
│   │   └── report.py
│   ├── models/
│   ├── templates/
│   └── static/
├── tests/
│   ├── test_validation.py
│   ├── test_metrics.py
│   ├── test_confidence_intervals.py
│   ├── test_comparison.py
│   ├── test_decision_engine.py
│   └── test_report.py
├── examples/
├── docs/
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

Cette structure est indicative et peut être adaptée aux besoins réels. Ne pas créer de modules vides ou de couches inutiles uniquement pour respecter cette arborescence.

---

## 12. Sécurité, confidentialité et gestion des données

Le MVP doit privilégier une exécution locale et limiter les transferts de données.

### Exigences

- Pas d’appels externes à des LLM ou à des API pour analyser les données.
- Pas d’exécution de code arbitraire fourni par l’utilisateur.
- Pas de désérialisation aveugle de fichiers pickle ou de modèles non fiables.
- Validation des chemins et protection contre les traversées de répertoires.
- Limites raisonnables de taille de fichier et gestion des erreurs.
- Pas d’inclusion inutile de données personnelles dans les rapports ou les logs.
- Pas de téléchargement automatique de datasets restreints.
- Pas de promesse de conformité réglementaire ou de sécurité absolue.

Le README doit expliquer les hypothèses de sécurité, les données utilisées dans la démonstration et les limites du mode local.

---

## 13. Démonstration sur imagerie médicale

### Projet candidat

Le dépôt existant de classification de tumeurs cérébrales par IRM peut servir de cas d’étude si les données, la licence et les artefacts sont appropriés :

`https://github.com/MousJB/brain-tumor-mri-classification`

Ne pas supposer que la structure du dataset, les splits ou les résultats sont corrects avant inspection.

### Étapes

1. Inspecter le dépôt, le dataset, sa licence et sa provenance.
2. Vérifier les partitions d’entraînement, validation et test.
3. Détecter les doublons exacts à l’aide de hashes cryptographiques.
4. Détecter les quasi-doublons avec une méthode de similarité adaptée.
5. Inspecter manuellement les cas signalés avant toute conclusion.
6. Si les ressources et les droits le permettent, entraîner deux versions réelles du modèle.
7. Enregistrer les configurations, graines, checkpoints et identifiants d’artefacts.
8. Générer des prédictions des deux versions sur les mêmes cas indépendants.
9. Utiliser MedVision QA pour comparer les prédictions et produire le rapport.
10. Documenter ce qui a été exécuté, ce qui ne l’a pas été et pourquoi.

### Si le dataset réel n’est pas prêt

La phase d’analyse d’images ne doit pas bloquer le MVP.

- Utiliser des fixtures ou des images synthétiques clairement étiquetées pour tester le pipeline.
- Si des fichiers de prédictions authentiques sont déjà disponibles et utilisables, les exploiter pour démontrer la comparaison sans réentraîner les modèles.
- Expliquer dans le README pourquoi l’analyse réelle ou le réentraînement n’a pas été réalisé.
- Ne jamais présenter des données synthétiques comme des données cliniques réelles.

### Interprétation des doublons

- Un hash identique signale un contenu identique au niveau des fichiers.
- Une similarité perceptuelle signale une ressemblance à examiner.
- Un quasi-doublon ne prouve pas l’identité d’un patient.
- La présence d’un doublon ne prouve pas automatiquement une fuite de données.
- Toute affirmation sur une fuite doit être fondée sur la provenance, les partitions et une inspection documentée.

### Tests de robustesse

Des tests synthétiques peuvent étudier l’effet de bruit gaussien ou de réduction de résolution sur les prédictions, si le pipeline d’image le permet.

Ils doivent être présentés comme des tests de sensibilité synthétiques. Ils ne reproduisent pas nécessairement les conditions réelles d’acquisition clinique et ne constituent pas une validation clinique.

---

## 14. Plan de développement sur 30 jours

Le calendrier est une cible, pas une obligation de livrer des fonctionnalités non validées. Chaque phase ne passe à la suivante qu’après réussite de ses tests et revue des résultats.

### Phase 0 — Cadrage et inspection (jours 1–3)

- Inspecter le dépôt, l’environnement et les données existantes.
- Confirmer les formats de prédiction.
- Définir les schémas et les conventions de classes.
- Définir les critères d’acceptation et les métadonnées.
- Vérifier les licences et droits d’usage des données.
- Créer le squelette du dépôt, les tests et le README initial.

**Gate :** schéma et périmètre documentés ; environnement reproductible ; tests de base exécutables.

### Phase 1 — Validation, métriques et intervalles de confiance (jours 4–9)

- Validation stricte des CSV.
- Alignement explicite des cas.
- Métriques de classification.
- Matrice de confusion.
- Bootstrap et intervalles de confiance adaptés.
- Tests unitaires sur cas normaux, limites et erreurs.
- Documentation des métriques et comportements non définis.

**Gate :** tests verts ; valeurs vérifiées sur des exemples contrôlés ; aucune suppression silencieuse de données ; aucune métrique non définie présentée comme valide.

### Phase 2 — Comparaison statistique et décision (jours 10–14)

- Comparaison de deux versions sur les mêmes cas.
- McNemar lorsque les conditions sont satisfaites.
- AUROC et méthode de comparaison adaptée si des scores sont disponibles.
- Validation indépendante de DeLong si possible ; sinon, ne pas revendiquer sa validation.
- Moteur de décision `SATISFIED`, `NOT_SATISFIED`, `INCONCLUSIVE`.
- Tests sur les limites, hypothèses et états non concluants.

**Gate :** méthodes correctement sélectionnées ; critères préétablis ; tests verts ; conclusion justifiée et traçable.

### Phase 3 — Rapport HTML (jours 15–17)

- Générer le Version Verification Record.
- Inclure les métadonnées disponibles et identifier celles qui manquent.
- Inclure la justification de taille d’échantillon selon ses quatre états.
- Ajouter “What This Report Cannot Establish”.
- Tester la génération et la lisibilité du rapport.
- Vérifier que le rapport n’invente aucune donnée.

**Gate :** rapport reproductible, lisible, cohérent avec les calculs et explicitement limité dans ses conclusions.

### Phase 4 — Analyse d’images et robustesse, conditionnelle (jours 18–23)

- Inspecter le dataset réel si disponible et autorisé.
- Détecter les doublons exacts et les quasi-doublons.
- Examiner les résultats signalés.
- Réaliser des tests de sensibilité synthétiques.
- Entraîner deux versions réelles uniquement si les données, licences, ressources et délais le permettent.
- Sinon, utiliser des fixtures synthétiques ou des prédictions authentiques déjà disponibles, en indiquant clairement les limites.

**Gate :** résultats traçables et correctement étiquetés ; aucune affirmation non étayée sur la fuite de données ou les performances.

**Important :** cette phase est conditionnelle. Son indisponibilité ne bloque pas le MVP principal.

### Phase 5 — Interface et workflow de bout en bout (jours 24–27)

- Routes FastAPI.
- Formulaires et pages Jinja2.
- Import et validation des fichiers.
- Lancement d’une évaluation.
- Affichage des résultats et critères.
- Historique local avec SQLite.
- Téléchargement du rapport HTML.
- Tests end-to-end.

**Gate :** un utilisateur peut réaliser le workflow principal de bout en bout sans manipulation manuelle du code.

### Finalisation (jours 28–30)

- Rejouer tous les tests.
- Corriger les problèmes bloquants.
- Vérifier les instructions d’installation.
- Préparer une démonstration reproductible.
- Ajouter des captures d’écran si elles apportent une vraie valeur.
- Finaliser le README et les limites connues.
- Préparer une courte présentation portfolio et une vidéo de démonstration, si utile.

---

## 15. Stratégie de tests

### Tests unitaires

- valeurs attendues des métriques sur des cas simples ;
- labels absents et classes déséquilibrées ;
- colonnes manquantes et supplémentaires ;
- identifiants dupliqués ;
- valeurs manquantes et non finies ;
- scores hors bornes ;
- ordre des classes incohérent ;
- cas non appariés ;
- intervalles de confiance avec graines reproductibles ;
- critères satisfaits, non satisfaits et inconclusifs ;
- états de justification d’échantillon ;
- rapport complet et métadonnées manquantes.

### Tests statistiques

- comparaison avec des résultats calculés indépendamment ;
- cas où les hypothèses d’un test ne sont pas satisfaites ;
- vérification des directions d’effet ;
- vérification de la logique de non-infériorité ;
- tests qui démontrent qu’un résultat non significatif ne produit pas automatiquement une conclusion d’équivalence.

### Tests d’intégration

- import CSV ;
- validation ;
- calcul des métriques ;
- comparaison des versions ;
- évaluation des critères ;
- enregistrement SQLite ;
- génération et téléchargement du rapport.

### Qualité minimale attendue

- tests automatisés exécutables en local ;
- pas d’erreurs silencieuses ;
- erreurs explicites et actionnables ;
- résultats reproductibles dans les limites des méthodes employées ;
- documentation des hypothèses et des limites.

Ne pas annoncer « tous les tests passent » sans avoir réellement exécuté la suite dans l’environnement concerné.

---

## 16. Risques et mesures d’atténuation

| Risque | Mesure |
|---|---|
| Dataset réel indisponible | Continuer le MVP avec des tests contrôlés ; rendre la phase image conditionnelle |
| Licence ou provenance incertaine | Ne pas utiliser les données avant clarification ; documenter les droits |
| Complexité statistique excessive | Implémenter les méthodes progressivement ; ne pas exposer une méthode non validée |
| DeLong non vérifié | Ne pas revendiquer la validation ; utiliser un bootstrap apparié testé ou marquer l’option indisponible |
| Périmètre trop large | Garder le noyau CSV → métriques → comparaison → décision → rapport |
| Conclusion scientifique excessive | États explicites, limites visibles, critères préétablis |
| Données sensibles | Exécution locale, minimisation, pas d’appels externes |
| Faux signal de fuite de données | Revue des doublons et vérification de provenance avant toute conclusion |

---

## 17. Indicateurs de réussite

### Réussite technique du MVP

- un fichier valide peut être évalué ;
- un fichier invalide est rejeté avec des explications ;
- les métriques sont testées sur des cas de référence ;
- deux versions peuvent être comparées sur des cas appariés ;
- les critères sont évalués selon des règles explicites ;
- les états inconclusifs sont correctement représentés ;
- le rapport HTML est généré et reproductible ;
- les limites et données manquantes sont visibles ;
- l’installation et la démonstration sont documentées.

### Réussite portfolio

- une personne extérieure peut comprendre le problème et lancer la démonstration ;
- les tests peuvent être exécutés ;
- les résultats affichés sont réels et vérifiables ;
- le rapport expose les hypothèses et les limites ;
- le projet permet de discuter de choix scientifiques et techniques en entretien.

---

## 18. Règles de développement avec Claude Code

Le projet doit être développé **phase par phase**, pas en demandant à l’outil de générer toute l’application en une seule fois.

### Règles de travail

1. Inspecter d’abord le dépôt et l’environnement existants.
2. Lire les fichiers et préserver le travail déjà présent.
3. Énoncer le périmètre exact de la phase en cours.
4. Implémenter uniquement cette phase.
5. Écrire les tests en même temps que le code.
6. Exécuter les tests et corriger les échecs.
7. Vérifier les calculs critiques par des exemples indépendants.
8. Ne jamais inventer des résultats, des données, des hashes, des références ou des validations.
9. Documenter les méthodes non disponibles et les limites.
10. Résumer les fichiers créés/modifiés, les tests réellement exécutés, leurs résultats et les problèmes restants.
11. Ne passer à la phase suivante que lorsque la phase actuelle satisfait son gate.
12. Si un prérequis manque, expliquer le blocage et proposer une alternative qui ne compromette pas l’intégrité scientifique.

### Première instruction à Claude Code

> Commence par inspecter le dépôt et l’environnement. Lis la spécification complète `MEDVISION_QA.md`. Implémente uniquement la Phase 1 : validation stricte des CSV, alignement explicite des cas, métriques de classification, matrice de confusion, intervalles de confiance bootstrap lorsque leur application est appropriée, et tests automatisés. N’implémente pas encore l’interface complète, la comparaison statistique avancée, la génération finale du rapport ou les fonctionnalités de la Phase 4. Ne supprime aucune ligne silencieusement, n’invente aucune donnée et ne remplace pas les valeurs invalides par des valeurs par défaut. Ajoute des tests pour les cas normaux, limites et invalides. Exécute la suite de tests, corrige les échecs et termine par un résumé factuel des fichiers modifiés, des tests exécutés, des résultats et des limites. Ne déclare pas la Phase 1 terminée si les tests ou les vérifications ne sont pas concluants.

---

## 19. Décisions finales

- **Nom :** MedVision QA.
- **Livrable central :** Version Verification Record au format HTML.
- **Objectif :** évaluation comparative reproductible et documentation technique des versions de modèles de classification d’images médicales.
- **Stack MVP :** Python, FastAPI, Jinja2, SQLite, NumPy/SciPy/scikit-learn, pytest.
- **Développement :** par phases avec tests verts comme gates.
- **Frontend :** pas de Next.js dans le MVP.
- **Données réelles :** souhaitées pour une démonstration forte, mais non requises pour débloquer le noyau technique.
- **DeLong :** validation indépendante si possible ; aucune revendication de validation sans preuve.
- **Taille d’échantillon :** état explicite, aucune justification inventée.
- **Rapport :** limites et non-objectifs visibles.
- **Réglementation :** aucune revendication de certification ou de conformité.
- **Durée cible :** 30 jours, ajustable selon les résultats, les données et les contraintes.

## Conclusion

MedVision QA doit être un outil d’évaluation technique modeste dans ses promesses, solide dans ses calculs et transparent dans ses limites. Sa valeur portfolio vient moins du nombre de fonctionnalités que de la qualité des validations, de la rigueur statistique, de la reproductibilité et de la capacité à produire un rapport que d’autres personnes peuvent examiner et comprendre.
