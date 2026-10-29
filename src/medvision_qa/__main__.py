"""Command line: ``python -m medvision_qa config.toml -o report.html [--lang ja]``.

Exit code: 0 if the report is generated (whatever the decision), 2 if the configuration
or the data are invalid (no report is produced then).
"""

import argparse
import sys
from pathlib import Path

from medvision_qa.classes import ConfigError
from medvision_qa.evaluation import run_evaluation
from medvision_qa.i18n import DEFAULT_LANGUAGE, LANGUAGES
from medvision_qa.report import write_report
from medvision_qa.validation import ValidationError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m medvision_qa",
                                     description="Generates an HTML Version Verification Record.")
    parser.add_argument("config", type=Path, help="TOML configuration file")
    parser.add_argument("-o", "--output", type=Path, required=True, help="HTML file to write")
    parser.add_argument("--lang", choices=LANGUAGES, default=DEFAULT_LANGUAGE,
                        help="report language (default: en)")
    args = parser.parse_args(argv)

    try:
        result = run_evaluation(args.config)
    except ConfigError as exc:
        print(f"Invalid configuration: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(f"Invalid data, no report produced.\n{exc}", file=sys.stderr)
        return 2

    path = write_report(result, args.output, lang=args.lang)
    print(f"{result.decision.state} — {result.decision.reason}")
    print(f"Report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
