import tomllib
from pathlib import Path

import medvision_qa

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_pyproject():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert medvision_qa.__version__ == pyproject["project"]["version"]


def test_core_dependencies_importable():
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import sklearn  # noqa: F401


def test_phase0_documents_exist():
    for doc in ("README.md", "MEDVISION_QA.md", "docs/data_format.md",
                "docs/evaluation_config.md", "docs/phase0_inspection.md", "docs/metrics.md"):
        assert (ROOT / doc).is_file(), doc
