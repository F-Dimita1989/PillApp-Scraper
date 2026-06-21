"""Utility di normalizzazione testo."""

from drug_image_fetcher.normalize.compare import (
    compare_dosage,
    compare_pharmaceutical_form,
    compare_quantity,
    dosage_tokens_match,
    forms_are_compatible,
    quantities_match,
)
from drug_image_fetcher.normalize.text import (
    normalize_aic,
    normalize_spaces,
    normalize_text,
    remove_accents,
    tokenize,
)

__all__ = [
    "compare_dosage",
    "compare_pharmaceutical_form",
    "compare_quantity",
    "dosage_tokens_match",
    "forms_are_compatible",
    "normalize_aic",
    "normalize_spaces",
    "normalize_text",
    "quantities_match",
    "remove_accents",
    "tokenize",
]
