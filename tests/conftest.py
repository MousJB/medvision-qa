"""Shared fixtures. All test data are synthetic."""

import pytest

from medvision_qa.classes import ClassSpec

MRI_CLASSES = ("glioma", "meningioma", "notumor", "pituitary")
TUMOR = ("glioma", "meningioma", "pituitary")


@pytest.fixture
def classes():
    return ClassSpec(MRI_CLASSES, TUMOR)


@pytest.fixture
def write_csv(tmp_path):
    """Writes a CSV from raw text (exact control of the bytes) and returns its path."""
    counter = iter(range(10_000))

    def _write(text: str, name: str | None = None, encoding: str = "utf-8"):
        path = tmp_path / (name or f"file_{next(counter)}.csv")
        path.write_bytes(text.encode(encoding))
        return path

    return _write
