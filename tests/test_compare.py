"""Test confronto dosaggio, forma e quantità."""

from drug_image_fetcher.normalize.compare import (
    MatchLevel,
    compare_dosage,
    compare_pharmaceutical_form,
    compare_quantity,
)


def test_compare_dosage_exact() -> None:
    result = compare_dosage("500 mg", "Confezione da 20 compresse da 500 mg")
    assert result.level == MatchLevel.EXACT
    assert result.score == 1.0


def test_compare_dosage_mismatch() -> None:
    result = compare_dosage("250 mg", "Compresse da 500 mg")
    assert result.level == MatchLevel.MISMATCH


def test_compare_form_compresse() -> None:
    result = compare_pharmaceutical_form(
        "compresse",
        "20 compresse rivestite con film",
    )
    assert result.level == MatchLevel.EXACT


def test_compare_form_mismatch_sciroppo_vs_compresse() -> None:
    result = compare_pharmaceutical_form("sciroppo", "20 compresse")
    assert result.level == MatchLevel.MISMATCH


def test_compare_quantity_exact() -> None:
    result = compare_quantity("20 compresse", "Confezione da 20 compresse")
    assert result.level == MatchLevel.EXACT


def test_compare_quantity_mismatch() -> None:
    result = compare_quantity("10 compresse", "Confezione da 20 compresse")
    assert result.level == MatchLevel.MISMATCH
