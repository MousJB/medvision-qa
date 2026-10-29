"""Fixtures communes. Toutes les données de test sont synthétiques."""

import pytest

from medvision_qa.classes import ClassSpec

IRM_CLASSES = ("glioma", "meningioma", "notumor", "pituitary")
TUMOR = ("glioma", "meningioma", "pituitary")


@pytest.fixture
def classes():
    return ClassSpec(IRM_CLASSES, TUMOR)


@pytest.fixture
def write_csv(tmp_path):
    """Écrit un CSV à partir d'un texte brut (contrôle exact des octets) et renvoie le chemin."""
    counter = iter(range(10_000))

    def _write(text: str, name: str | None = None, encoding: str = "utf-8"):
        path = tmp_path / (name or f"file_{next(counter)}.csv")
        path.write_bytes(text.encode(encoding))
        return path

    return _write
