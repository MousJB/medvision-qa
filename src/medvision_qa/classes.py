"""Déclaration des classes et de la tâche binaire dérivée (docs/data_format.md § 2)."""

import re
from dataclasses import dataclass

CLASS_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ConfigError(ValueError):
    """Paramètre fourni par l'utilisateur invalide (classes, options statistiques...)."""


@dataclass(frozen=True)
class ClassSpec:
    """Classes déclarées, dans l'ordre qui fixe la matrice de confusion et les scores.

    ``positive`` : classes positives de la tâche binaire dérivée (vide = pas de tâche
    binaire ; sensibilité, spécificité et AUROC seront alors indéfinies).
    """

    order: tuple[str, ...]
    positive: tuple[str, ...] = ()

    def __post_init__(self):
        if isinstance(self.order, str):
            raise ConfigError("`order` doit être une liste de classes, pas une chaîne.")
        if isinstance(self.positive, str):
            raise ConfigError("`positive` doit être une liste de classes, pas une chaîne : "
                              f'écrire ["{self.positive}"].')
        object.__setattr__(self, "order", tuple(self.order))
        object.__setattr__(self, "positive", tuple(self.positive))

        if len(self.order) < 2:
            raise ConfigError("Au moins 2 classes doivent être déclarées.")
        for name in self.order:
            if not isinstance(name, str) or not CLASS_NAME_PATTERN.fullmatch(name):
                raise ConfigError(f"Nom de classe invalide : {name!r} "
                                  "(caractères autorisés : lettres, chiffres, _ et -).")
        duplicates = sorted({c for c in self.order if self.order.count(c) > 1})
        if duplicates:
            raise ConfigError(f"Classes déclarées plusieurs fois : {duplicates}.")

        unknown = [c for c in self.positive if c not in self.order]
        if unknown:
            raise ConfigError(f"Classes positives non déclarées : {unknown}.")
        if len(set(self.positive)) != len(self.positive):
            raise ConfigError("Classe positive déclarée plusieurs fois.")
        if self.positive and set(self.positive) == set(self.order):
            raise ConfigError("Les classes positives ne peuvent pas être toutes les classes : "
                              "la tâche binaire n'aurait pas de classe négative.")

    @property
    def index(self) -> dict[str, int]:
        return {name: i for i, name in enumerate(self.order)}

    @property
    def positive_indices(self) -> tuple[int, ...]:
        idx = self.index
        return tuple(idx[c] for c in self.positive)

    @property
    def score_columns(self) -> tuple[str, ...]:
        return tuple(f"score_{c}" for c in self.order)
