"""Confronto strutturato di dosaggio, forma farmaceutica e quantità."""

from __future__ import annotations

import re
from enum import Enum
from typing import NamedTuple

from drug_image_fetcher.normalize.text import normalize_text, tokenize


class MatchLevel(str, Enum):
    EXACT = "exact"
    COMPATIBLE = "compatible"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class FieldComparison(NamedTuple):
    level: MatchLevel
    detail: str
    score: float  # 0.0 – 1.0 contributo normalizzato


_DOSAGE_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(mg|g|mcg|µg|ug|ml|ui|u\.i\.?|%)",
    re.IGNORECASE,
)
_QUANTITY_RE = re.compile(
    r"(\d+)\s*(?:compresse?|cpr|c\.?p\.?r\.?|capsule?|cps|bustine?|fiale?|"
    r"flaconi?|ml|g|dosi|unita|unità|pz|pezzi?|stick|cerotti?|supposte?|"
    r"ovuli?|patch|iniettabili?|siringhe?)",
    re.IGNORECASE,
)

_FORM_SYNONYMS: dict[str, set[str]] = {
    "compresse": {"compressa", "compresse", "cpr", "cp", "tablet", "tablets", "pillole"},
    "capsule": {"capsula", "capsule", "cps", "caps", "gelule", "gelules"},
    "bustine": {"bustina", "bustine", "sachet", "sachets", "stick", "sticks"},
    "sciroppo": {"sciroppo", "sciroppi", "syrup", "soluzione orale"},
    "gocce": {"gocce", "gocce orali", "drops"},
    "fiale": {"fiala", "fiale", "ampolla", "ampolle", "iniettabile", "iniettabili"},
    "crema": {"crema", "creme", "pomata", "pomate", "unguento", "unguenti"},
    "supposte": {"supposta", "supposte"},
    "ovuli": {"ovulo", "ovuli"},
    "cerotti": {"cerotto", "cerotti", "patch", "transdermico", "transdermica"},
    "spray": {"spray", "sprays", "aerosol"},
    "soluzione": {"soluzione", "soluzioni", "solution"},
    "sospensione": {"sospensione", "sospensioni", "suspension"},
}


def _canonical_form(form_text: str) -> str | None:
    normalized = normalize_text(form_text)
    if not normalized:
        return None
    tokens = set(normalized.split())
    for canonical, synonyms in _FORM_SYNONYMS.items():
        if tokens & synonyms or normalized in synonyms:
            return canonical
    for canonical, synonyms in _FORM_SYNONYMS.items():
        if any(syn in normalized for syn in synonyms):
            return canonical
    return None


def extract_dosage_values(text: str) -> list[tuple[float, str]]:
    values: list[tuple[float, str]] = []
    for match in _DOSAGE_RE.finditer(text):
        amount = float(match.group(1).replace(",", "."))
        unit = match.group(2).lower().replace("µ", "u").replace(".", "")
        if unit.startswith("u") and "i" in unit:
            unit = "ui"
        values.append((amount, unit))
    return values


def extract_quantities(text: str) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []
    for match in _QUANTITY_RE.finditer(text):
        count = int(match.group(1))
        unit_fragment = normalize_text(match.group(0))
        results.append((count, unit_fragment))
    return results


def compare_dosage(expected: str | None, page_text: str) -> FieldComparison:
    if not expected:
        return FieldComparison(MatchLevel.UNKNOWN, "dosaggio non fornito", 0.0)

    expected_values = extract_dosage_values(expected)
    page_values = extract_dosage_values(page_text)

    if not expected_values:
        if dosage_tokens_match(expected, page_text):
            return FieldComparison(MatchLevel.PARTIAL, "dosaggio testuale parziale", 0.6)
        return FieldComparison(MatchLevel.UNKNOWN, "dosaggio atteso non parsabile", 0.0)

    if not page_values:
        if dosage_tokens_match(expected, page_text):
            return FieldComparison(MatchLevel.PARTIAL, "dosaggio menzionato senza unità", 0.5)
        return FieldComparison(MatchLevel.MISMATCH, "dosaggio assente nella pagina", 0.0)

    for exp_amount, exp_unit in expected_values:
        for page_amount, page_unit in page_values:
            if exp_unit == page_unit and abs(exp_amount - page_amount) < 0.01:
                return FieldComparison(MatchLevel.EXACT, f"{exp_amount} {exp_unit}", 1.0)

    # Penalizza dosaggi diversi sulla stessa unità
    exp_units = {u for _, u in expected_values}
    for exp_amount, exp_unit in expected_values:
        for page_amount, page_unit in page_values:
            if exp_unit == page_unit and exp_amount != page_amount:
                return FieldComparison(
                    MatchLevel.MISMATCH,
                    f"dosaggio diverso: atteso {exp_amount}{exp_unit}, trovato {page_amount}{page_unit}",
                    0.0,
                )

    if exp_units & {u for _, u in page_values}:
        return FieldComparison(MatchLevel.PARTIAL, "unità compatibile, valore incerto", 0.4)

    return FieldComparison(MatchLevel.MISMATCH, "dosaggio non corrispondente", 0.0)


def dosage_tokens_match(expected: str, page_text: str) -> bool:
    return normalize_text(expected) in normalize_text(page_text)


def compare_pharmaceutical_form(
    expected: str | None, page_text: str
) -> FieldComparison:
    if not expected:
        return FieldComparison(MatchLevel.UNKNOWN, "forma non fornita", 0.0)

    expected_canonical = _canonical_form(expected)
    page_canonical = _canonical_form(page_text)

    if expected_canonical and page_canonical:
        if expected_canonical == page_canonical:
            return FieldComparison(MatchLevel.EXACT, expected_canonical, 1.0)
        if forms_are_compatible(expected_canonical, page_canonical):
            return FieldComparison(MatchLevel.COMPATIBLE, "forma simile", 0.5)
        return FieldComparison(
            MatchLevel.MISMATCH,
            f"forma diversa: {expected_canonical} vs {page_canonical}",
            0.0,
        )

    if normalize_text(expected) in normalize_text(page_text):
        return FieldComparison(MatchLevel.EXACT, expected, 1.0)

    return FieldComparison(MatchLevel.MISMATCH, "forma non rilevata", 0.0)


def forms_are_compatible(a: str, b: str) -> bool:
    """Compatibilità limitata — usata solo per segnalare incertezza, non match forte."""
    compatible_groups = [
        {"compresse", "capsule"},
        {"crema", "pomata", "unguento"},
        {"soluzione", "sciroppo", "gocce"},
    ]
    for group in compatible_groups:
        if a in group and b in group:
            return True
    return False


def compare_quantity(expected: str | None, page_text: str) -> FieldComparison:
    if not expected:
        return FieldComparison(MatchLevel.UNKNOWN, "quantità non fornita", 0.0)

    expected_qty = extract_quantities(expected)
    page_qty = extract_quantities(page_text)

    if expected_qty and page_qty:
        exp_count, _ = expected_qty[0]
        for page_count, _ in page_qty:
            if page_count == exp_count:
                return FieldComparison(MatchLevel.EXACT, f"{exp_count} unità", 1.0)
        return FieldComparison(
            MatchLevel.MISMATCH,
            f"quantità diversa: atteso {exp_count}, trovato {[c for c, _ in page_qty]}",
            0.0,
        )

    # Fallback numerico semplice
    expected_digits = re.findall(r"\d+", expected)
    if expected_digits:
        target = expected_digits[0]
        page_tokens = tokenize(page_text)
        if target in page_tokens:
            return FieldComparison(MatchLevel.PARTIAL, f"numero {target} presente", 0.6)

    return FieldComparison(MatchLevel.MISMATCH, "quantità non corrispondente", 0.0)


def quantities_match(expected: str | None, page_text: str) -> bool:
    return compare_quantity(expected, page_text).level in {
        MatchLevel.EXACT,
        MatchLevel.PARTIAL,
    }
