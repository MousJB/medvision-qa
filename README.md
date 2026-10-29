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
| 1 | Validation CSV, métriques, intervalles de confiance | à faire |
| 2 | Comparaison statistique, moteur de décision | à faire |
| 3 | Rapport HTML | à faire |
| 4 | Analyse d'images IRM (conditionnelle) | à faire |
| 5 | Interface FastAPI | à faire |

Aucune fonctionnalité d'évaluation n'est encore implémentée.

## Documentation

- [MEDVISION_QA.md](MEDVISION_QA.md) : spécification complète
- [docs/data_format.md](docs/data_format.md) : format des CSV d'entrée et règles de validation
- [docs/evaluation_config.md](docs/evaluation_config.md) : configuration, critères d'acceptation, règles de décision
- [docs/phase0_inspection.md](docs/phase0_inspection.md) : inspection de l'environnement, du dépôt IRM et du dataset

## Installation (développement)

Python ≥ 3.11.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
pytest
```

Pour reproduire exactement l'environnement testé : `pip install -r requirements-lock.txt`
puis `pip install -e . --no-deps`.

## Données et sécurité

- Exécution locale uniquement : aucun appel réseau, aucun appel à un LLM ou à une API
  externe pour analyser les données.
- Aucun dataset n'est inclus ni téléchargé automatiquement. Le `.gitignore` exclut
  `data/`, les images médicales et les poids de modèles.
- Pas de chargement de fichiers pickle ni de modèles : l'outil ne lit que des CSV et une
  configuration TOML.
- Les tests des phases 1 à 3 utilisent des données synthétiques, toujours identifiées
  comme telles.
