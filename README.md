# MedVision QA

Outil de vérification comparative et de documentation technique des versions de modèles de
classification d'images médicales.

À partir des prédictions de deux versions d'un modèle sur les mêmes cas, MedVision QA doit
valider les données, calculer des métriques avec leur incertitude, appliquer des critères
d'acceptation définis à l'avance et produire un rapport HTML : le *Version Verification
Record*.

> **MedVision QA n'est pas un dispositif médical**, ni un outil de diagnostic, ni une
> validation clinique, ni une preuve de conformité réglementaire (ISO 13485, FDA QMSR
> ou autre).

## État d'avancement

| Phase | Contenu | État |
|---|---|---|
| 0 | Cadrage, formats, environnement | terminée |
| 1 | Validation CSV, métriques, intervalles de confiance | terminée (API Python) |
| 2 | Comparaison statistique, moteur de décision | terminée (API Python) |
| 3 | Rapport HTML | terminée (ligne de commande) |
| 4 | Analyse d'images IRM réelles | terminée : [experiments/brain_mri/](experiments/brain_mri/README.md) |
| 5 | Interface web locale (FastAPI) | terminée |

## Résultat sur données IRM réelles

Deux versions entraînées sur le dataset public figshare (CC BY 4.0), test disjoint par
patient (64 patients), critères fixés avant entraînement : **INCONCLUSIVE**. ResNet18 est
non inférieure à SimpleCNN et a une meilleure AUROC, mais sa sensibilité gliome (0,929,
IC [0,865 ; 0,970]) ne démontre pas le seuil de 0,90. L'audit des données a aussi relevé
des identifiants patient dupliqués dans figshare et **16,5 % d'images de test copiées dans
l'entraînement** dans le dataset Kaggle MRI-BT. Détails :
[experiments/brain_mri/README.md](experiments/brain_mri/README.md).

## Démonstration (données synthétiques)

Interface web (import des fichiers, résultat, historique, téléchargement du rapport) :

```bash
python -m medvision_qa.web        # puis ouvrir http://127.0.0.1:8000
```

Les fichiers de démonstration sont téléchargeables depuis la page d'accueil. En ligne de
commande :

```bash
python -m medvision_qa examples/synthetic_demo/config.toml -o reports/demo.html
```

Les CSV de [examples/synthetic_demo/](examples/synthetic_demo/) sont **synthétiques** :
872 images simulées pour 450 patients. Ils sont régénérables à l'octet près avec
`python examples/synthetic_demo/generate.py`. Le rapport le signale par un bandeau.

## Utilisation

À partir d'une configuration TOML ([exemple](docs/evaluation_config.md#1-exemple-complet)) :

```bash
python -m medvision_qa config.toml -o rapport.html
```

Ou depuis Python :

```python
from medvision_qa.evaluation import run_evaluation

result = run_evaluation("config.toml")
print(result.decision.state, "-", result.decision.reason)
for c in result.decision.criteria:
    print(c.criterion.id, c.state, c.reason)
```

Une entrée invalide lève `ValidationError`, dont `.issues` liste toutes les violations
(fichier, ligne, colonne, valeur, règle). Une configuration invalide lève `ConfigError`.

## Documentation

- [MEDVISION_QA.md](MEDVISION_QA.md) : spécification complète
- [docs/data_format.md](docs/data_format.md) : format des CSV d'entrée et règles de validation
- [docs/metrics.md](docs/metrics.md) : définitions des métriques, cas indéfinis, bootstrap, limites
- [docs/evaluation_config.md](docs/evaluation_config.md) : configuration, critères d'acceptation, règles de décision
- [docs/comparison.md](docs/comparison.md) : comparaison appariée A/B, McNemar, statut de DeLong, traçabilité
- [docs/report.md](docs/report.md) : contenu du Version Verification Record et propriétés garanties
- [docs/web.md](docs/web.md) : interface web, stockage local, mesures de sécurité
- [docs/phase0_inspection.md](docs/phase0_inspection.md) : inspection de l'environnement, du dépôt IRM et du dataset

## Installation (développement)

Python ≥ 3.11.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"      # bibliothèque + interface web + outils de test
pytest
```

`pip install -e .` seul installe le cœur (validation, statistiques, rapport, ligne de
commande) sans FastAPI. L'extra `[web]` ajoute l'interface.

Pour reproduire exactement l'environnement testé : `pip install -r requirements-lock.txt`
puis `pip install -e . --no-deps`.

## Données et sécurité

- Exécution locale uniquement : aucun appel réseau, aucun appel à un LLM ou à une API
  externe pour analyser les données. L'interface web n'écoute que sur `127.0.0.1` et ne
  doit pas être exposée sur un réseau (pas d'authentification).
- Aucun dataset n'est inclus ni téléchargé automatiquement. Le `.gitignore` exclut
  `data/`, les images médicales et les poids de modèles.
- Pas de chargement de fichiers pickle ni de modèles : l'outil ne lit que des CSV et une
  configuration TOML.
- Les tests des phases 1 à 3 utilisent des données synthétiques, toujours identifiées
  comme telles.
