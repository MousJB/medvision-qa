"""Message catalog: both languages complete and consistent, every key used exists."""

import re
import string
from pathlib import Path

import pytest

from medvision_qa.i18n import CATALOG, MESSAGES, Text, msg, raw, t

SRC = Path(__file__).resolve().parents[1] / "src" / "medvision_qa"
JAPANESE = re.compile(r"[぀-ヿ一-鿿]")
# Entries whose Japanese text is legitimately identical to the English one.
SAME_IN_BOTH = {"raw", "state.SATISFIED", "state.NOT_SATISFIED", "state.INCONCLUSIVE"}


def placeholders(text):
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name)


@pytest.mark.parametrize("key", sorted(MESSAGES))
def test_both_languages_use_the_same_placeholders(key):
    en, ja = MESSAGES[key]
    assert placeholders(en) == placeholders(ja)


@pytest.mark.parametrize("key", sorted(MESSAGES))
def test_japanese_text_is_japanese(key):
    en, ja = MESSAGES[key]
    letters = re.sub(r"\{[^}]*\}", "", en)
    if key in SAME_IN_BOTH or key == "sep" or not re.search(r"[A-Za-z]{3}", letters):
        return
    assert JAPANESE.search(ja), f"{key}: {ja!r}"


def test_no_french_left_in_catalog():
    french = re.compile(r"[àâçéèêëîïôûùœ]|\b(le|la|les|des|une|pour|avec|sans)\b", re.I)
    for key, (en, _) in MESSAGES.items():
        assert not french.search(en), key


def test_every_key_used_in_code_and_templates_exists():
    code = "\n".join(p.read_text(encoding="utf-8") for p in SRC.rglob("*") if p.suffix in (".py", ".j2"))
    used = set(re.findall(r'\b(?:msg|_|t)\(\s*"([a-z_]+\.[A-Za-z0-9_.]+)"(?!\s*~)', code))
    assert used, "no key found: the pattern is out of date"
    assert used <= set(MESSAGES), used - set(MESSAGES)


def test_text_renders_nested_and_list_parameters():
    detail = (msg("cmp.undefined_detail", version="A", reason=msg("metric.no_scores")),
              msg("cmp.undefined_detail", version="B", reason=msg("metric.no_scores")))
    text = msg("cmp.undefined_for", details=detail)
    assert str(text) == "metric undefined for A: scores not provided; B: scores not provided"
    assert text.render("ja") == "指標が未定義: A（スコアが提供されていません）、B（スコアが提供されていません）"
    assert Text.from_dict(text.to_dict()) == text


def test_unknown_key_and_language_rejected():
    with pytest.raises(KeyError):
        msg("no.such.key")
    with pytest.raises(ValueError):
        t("r.title", "fr")


def test_raw_text_shown_as_is():
    assert raw("Invalid value (line 3)").render("ja") == "Invalid value (line 3)"
    assert set(CATALOG) == {"en", "ja"}
