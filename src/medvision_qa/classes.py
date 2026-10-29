"""Class declaration and derived binary task (docs/data_format.md § 2)."""

import re
from dataclasses import dataclass

from medvision_qa.i18n import Text, msg, raw

CLASS_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class ConfigError(ValueError):
    """Invalid user-supplied setting (classes, statistical options...).

    ``text`` holds the message so it can be rendered in any supported language.
    """

    def __init__(self, text: Text | str):
        self.text = text if isinstance(text, Text) else raw(text)
        super().__init__(str(self.text))


@dataclass(frozen=True)
class ClassSpec:
    """Declared classes, in the order that fixes the confusion matrix and the scores.

    ``positive``: positive classes of the derived binary task (empty = no binary task;
    sensitivity, specificity and AUROC are then undefined).
    """

    order: tuple[str, ...]
    positive: tuple[str, ...] = ()

    def __post_init__(self):
        if isinstance(self.order, str):
            raise ConfigError(msg("cfg.order_not_list"))
        if isinstance(self.positive, str):
            raise ConfigError(msg("cfg.positive_is_string", value=self.positive))
        object.__setattr__(self, "order", tuple(self.order))
        object.__setattr__(self, "positive", tuple(self.positive))

        if len(self.order) < 2:
            raise ConfigError(msg("cfg.too_few_classes"))
        for name in self.order:
            if not isinstance(name, str) or not CLASS_NAME_PATTERN.fullmatch(name):
                raise ConfigError(msg("cfg.class_name_invalid", name=repr(name)))
        duplicates = sorted({c for c in self.order if self.order.count(c) > 1})
        if duplicates:
            raise ConfigError(msg("cfg.class_duplicates", names=str(duplicates)))

        unknown = [c for c in self.positive if c not in self.order]
        if unknown:
            raise ConfigError(msg("cfg.positive_undeclared", names=str(unknown)))
        if len(set(self.positive)) != len(self.positive):
            raise ConfigError(msg("cfg.positive_duplicate"))
        if self.positive and set(self.positive) == set(self.order):
            raise ConfigError(msg("cfg.positive_all"))

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
