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


DOCS = ("data_format.md", "evaluation_config.md", "phase0_inspection.md", "phase4_data_sources.md",
        "metrics.md", "comparison.md", "report.md", "web.md")


def test_documents_exist_in_english_and_japanese():
    for doc in ("README.md", "README.ja.md", "MEDVISION_QA.md", "MEDVISION_QA.ja.md"):
        assert (ROOT / doc).is_file(), doc
    for doc in DOCS:
        assert (ROOT / "docs" / doc).is_file(), doc
        assert (ROOT / "docs" / "ja" / doc).is_file(), doc
    for doc in ("README", "PROTOCOL"):
        assert (ROOT / "experiments" / "brain_mri" / f"{doc}.ja.md").is_file(), doc
    assert (ROOT / "experiments" / "rsna_pneumonia" / "README.ja.md").is_file()
