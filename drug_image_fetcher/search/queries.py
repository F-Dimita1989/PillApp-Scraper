"""Generazione query di ricerca robuste da metadati farmaco."""

from __future__ import annotations

from drug_image_fetcher.models import DrugInfo
from drug_image_fetcher.normalize.text import normalize_aic, normalize_spaces


def build_search_queries(drug: DrugInfo, max_queries: int = 4) -> list[str]:
    """
    Costruisce query ordinate per precisione decrescente.

    La prima query è la più specifica (AIC + dettagli confezione).
    Le successive allargano leggermente il campo senza perdere i vincoli critici.
    """
    aic = normalize_aic(drug.aic)
    name = drug.name.strip()
    dosage = (drug.dosage or "").strip()
    form = (drug.pharmaceutical_form or "").strip()
    quantity = (drug.package_quantity or "").strip()
    company = (drug.marketing_authorization_holder or "").strip()
    substance = (drug.active_substance or "").strip()

    queries: list[str] = []

    # Query 1: massima specificità — AIC è l'identificatore univoco italiano
    if aic:
        parts = [aic, name]
        if dosage:
            parts.append(dosage)
        if form:
            parts.append(form)
        if quantity:
            parts.append(quantity)
        parts.append("confezione")
        queries.append(normalize_spaces(" ".join(parts)))

    # Query 2: AIC + nome + forma + quantità (senza parole extra)
    if aic and name:
        parts = [aic, name, form, quantity]
        queries.append(normalize_spaces(" ".join(p for p in parts if p)))

    # Query 3: nome commerciale completo con vincoli confezione
    if name:
        parts = [name, dosage, form, quantity, "farmaco", "immagine"]
        queries.append(normalize_spaces(" ".join(p for p in parts if p)))

    # Query 4: azienda + prodotto (utile per siti istituzionali)
    if company and name:
        parts = [company, name, dosage, form, quantity]
        queries.append(normalize_spaces(" ".join(p for p in parts if p)))

    # Query 5: principio attivo (generico: es. ibuprofene, paracetamolo)
    if substance:
        parts = [substance, dosage, form, quantity]
        queries.append(normalize_spaces(" ".join(p for p in parts if p)))

    # Deduplica preservando ordine
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        key = q.lower()
        if key not in seen and q:
            seen.add(key)
            unique.append(q)

    return unique[:max_queries]
