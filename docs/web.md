# Interface web locale — v0.1

Implémentation : `src/medvision_qa/web.py`, `src/medvision_qa/history.py`, gabarits
`src/medvision_qa/templates/web_*.html.j2`. Tests : `tests/test_web.py`,
`tests/test_history.py`.

```bash
pip install -e ".[web]"
python -m medvision_qa.web                # http://127.0.0.1:8000
python -m medvision_qa.web --port 8080 --data-dir D:/evaluations
```

## 1. Workflow

1. **Accueil** (`/`) : formulaire d'import et historique des évaluations.
2. Importer une configuration `.toml` et les CSV qu'elle référence (au plus 4). Les noms
   des CSV doivent correspondre aux chemins de la configuration. Les fichiers de la
   démonstration synthétique sont téléchargeables depuis l'accueil.
3. **Lancer** : validation, calculs et décision (quelques secondes), puis redirection vers
   la page de résultat.
4. **Résultat** (`/evaluations/<id>`) : conclusion globale et état de chaque critère avec
   sa justification. Liens pour ouvrir ou télécharger le Version Verification Record.
5. **Refus** (configuration ou données invalides) : la liste des erreurs est affichée
   (50 au plus, liste complète dans l'historique). Aucun rapport n'est produit et les
   fichiers importés sont **supprimés**.

## 2. Stockage local

```
medvision_data/
├── history.sqlite          # une ligne par évaluation, terminée ou refusée
└── runs/<id>/              # évaluations terminées uniquement
    ├── config.toml, *.csv  # fichiers importés, octet pour octet
    └── report.html
```

Le même identifiant (UUID4) sert pour l'exécution, le dossier, la ligne d'historique et
le rapport. Les fichiers étant conservés à l'identique, leurs SHA-256 dans le rapport
restent vérifiables. Le dossier `medvision_data/` est exclu de git.

## 3. Sécurité (spec § 12)

| Mesure | Détail |
|---|---|
| Écoute locale uniquement | `127.0.0.1`, pas d'option pour écouter sur le réseau |
| Aucun appel externe | aucune requête sortante, aucun JavaScript, aucune ressource distante |
| Noms de fichiers | `^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$`, sans dossier ; extension `.toml` / `.csv` ; pas de doublon |
| Taille | 50 Mo par fichier, 4 CSV au maximum |
| Chemins de la configuration | confinés au dossier de l'évaluation (`..` et chemins absolus refusés) |
| Identifiants dans l'URL | UUID4 validé par expression régulière, puis recherché dans l'historique |
| Contenu | seuls du CSV et du TOML sont lus ; rien n'est exécuté ni désérialisé autrement |
| En-têtes | CSP `default-src 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` |
| Échappement | tout texte utilisateur passe par l'échappement Jinja2 (testé avec une injection HTML) |
| SQL | requêtes paramétrées (testé) |
| Documentation d'API | `/docs`, `/redoc`, `/openapi.json` désactivés |

## 4. Limites

- Application mono-utilisateur, sans authentification ni protection CSRF : elle ne doit
  pas être exposée sur un réseau.
- Évaluation synchrone : la page attend la fin des calculs (environ 6 s pour la démo de
  872 cas avec 2 000 tirages).
- La configuration est importée telle quelle. Il n'y a pas de formulaire pour composer les
  critères : c'est voulu, puisque le fichier versionné est la trace des critères définis à
  l'avance.
- Pas de suppression d'évaluation depuis l'interface (supprimer le dossier et la ligne à
  la main).
