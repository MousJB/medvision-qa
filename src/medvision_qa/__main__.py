"""Ligne de commande : ``python -m medvision_qa config.toml -o rapport.html``.

Code de sortie : 0 si le rapport est généré (quelle que soit la décision), 2 si la
configuration ou les données sont invalides (aucun rapport n'est alors produit).
"""

import argparse
import sys
from pathlib import Path

from medvision_qa.classes import ConfigError
from medvision_qa.evaluation import run_evaluation
from medvision_qa.report import write_report
from medvision_qa.validation import ValidationError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m medvision_qa",
                                     description="Génère un Version Verification Record HTML.")
    parser.add_argument("config", type=Path, help="fichier de configuration TOML")
    parser.add_argument("-o", "--output", type=Path, required=True, help="fichier HTML à écrire")
    args = parser.parse_args(argv)

    try:
        result = run_evaluation(args.config)
    except ConfigError as exc:
        print(f"Configuration invalide : {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(f"Données invalides, aucun rapport produit.\n{exc}", file=sys.stderr)
        return 2

    path = write_report(result, args.output)
    print(f"{result.decision.state} — {result.decision.reason}")
    print(f"Rapport : {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
