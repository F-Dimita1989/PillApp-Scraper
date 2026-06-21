"""Test normalizzazione testo."""

from drug_image_fetcher.normalize.text import (
    normalize_aic,
    normalize_text,
    remove_accents,
    token_overlap_ratio,
    tokenize,
)


def test_remove_accents() -> None:
    assert remove_accents("Perché àèìòù") == "Perche aeiou"


def test_normalize_text() -> None:
    assert normalize_text("  Tachipirina®  500 MG  ") == "tachipirina 500 mg"


def test_tokenize() -> None:
    tokens = tokenize("Compresse rivestite 20 pezzi")
    assert "compresse" in tokens
    assert "pezzi" in tokens


def test_normalize_aic() -> None:
    assert normalize_aic("027606012") == "027606012"
    assert normalize_aic("27606012") == "027606012"


def test_token_overlap_ratio_exact() -> None:
    ratio = token_overlap_ratio("Tachipirina 500 mg", "Tachipirina 500 mg compresse")
    assert ratio >= 0.6
