"""Normalizzazione testo per confronti robusti."""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^\w\s./%-]", re.UNICODE)


def remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_spaces(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip())


def normalize_text(text: str) -> str:
    """Lowercase, rimozione accenti, spazi uniformi, punteggiatura leggera."""
    if not text:
        return ""
    cleaned = remove_accents(text.lower())
    cleaned = _NON_ALNUM_RE.sub(" ", cleaned)
    return normalize_spaces(cleaned)


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return [token for token in normalized.split(" ") if len(token) > 1]


# Token generici da ignorare nel match URL prodotto (non distinguono confezioni)
GENERIC_DRUG_TOKENS: frozenset[str] = frozenset({
    "mg", "ml", "g", "ui", "mcg", "compresse", "compressa", "cpr", "capsule",
    "capsula", "cps", "bustine", "bustina", "granulato", "granulati", "sciroppo",
    "gocce", "fiale", "fiala", "supposte", "supposta", "crema", "pomata",
    "farmaco", "confezione", "immagine", "compresse", "rivestite", "effervescente",
    "orale", "generico", "generics", "mylan", "sandoz", "teva", "doc", "spa",
})


def significant_name_tokens(name: str) -> list[str]:
    """Token del nome commerciale utili per match URL (es. Brufen, Tachipirina)."""
    return [
        t for t in tokenize(name)
        if t not in GENERIC_DRUG_TOKENS and not t.isdigit() and len(t) > 2
    ]


def normalize_aic(aic: str) -> str:
    """AIC italiano: 9 cifre, eventualmente con spazi."""
    digits = re.sub(r"\D", "", aic)
    return digits.zfill(9) if digits else ""


def contains_normalized_substring(haystack: str, needle: str) -> bool:
    return normalize_text(needle) in normalize_text(haystack)


def token_overlap_ratio(a: str, b: str) -> float:
    tokens_a = set(tokenize(a))
    tokens_b = set(tokenize(b))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    return len(intersection) / max(len(tokens_a), len(tokens_b))
