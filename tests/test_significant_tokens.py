"""Test token significativi per match generico farmaci."""

from drug_image_fetcher.normalize.text import significant_name_tokens


def test_significant_name_tokens_brufen() -> None:
    assert "brufen" in significant_name_tokens("Brufen")


def test_significant_name_tokens_excludes_generic() -> None:
    tokens = significant_name_tokens("OMEOPRAZOLO MYLAN GENERICS 20 MG")
    assert "mg" not in tokens
    assert "generics" not in tokens
    assert "omeoprazolo" in tokens
