"""Motore di scoring per pagine e immagini candidate."""

from __future__ import annotations

import re

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.models import CandidateImage, DrugInfo, PageMatch
from drug_image_fetcher.normalize.compare import (
    MatchLevel,
    compare_dosage,
    compare_pharmaceutical_form,
    compare_quantity,
)
from drug_image_fetcher.normalize.text import (
    normalize_aic,
    normalize_text,
    token_overlap_ratio,
    tokenize,
)
from drug_image_fetcher.search.trusted_sites import is_trusted_url

_GENERIC_PAGE_HINTS = re.compile(
    r"(cookie|privacy|login|registrati|newsletter|carrello|"
    r"termini e condizioni|home page|catalogo generico)",
    re.IGNORECASE,
)


class PageScorer:
    """Calcola rilevanza pagina + bonus immagine per ogni candidato."""

    def __init__(self, config: FetcherConfig) -> None:
        self._config = config

    def score_page(
        self,
        drug: DrugInfo,
        page_url: str,
        page_text: str,
        candidates: list[CandidateImage],
    ) -> list[PageMatch]:
        if not candidates:
            return [
                PageMatch(
                    source_page_url=page_url,
                    page_text=page_text,
                    candidates=[],
                    relevance_score=0.0,
                    rejected_reasons=["nessuna immagine candidata"],
                )
            ]

        base_score, matched, rejected, field_scores = self._score_page_content(
            drug, page_text, page_url
        )

        results: list[PageMatch] = []
        for candidate in candidates:
            image_bonus, image_rejected = self._score_image(candidate, drug)
            total = max(0.0, min(1.0, base_score + image_bonus))
            all_rejected = list(rejected) + image_rejected

            results.append(
                PageMatch(
                    source_page_url=page_url,
                    page_text=page_text,
                    candidates=[candidate],
                    relevance_score=total,
                    matched_fields=list(matched),
                    rejected_reasons=all_rejected,
                    field_scores=dict(field_scores),
                )
            )

        return results

    def _score_page_content(
        self,
        drug: DrugInfo,
        page_text: str,
        page_url: str,
    ) -> tuple[float, list[str], list[str], dict[str, float]]:
        score = 0.0
        matched: list[str] = []
        rejected: list[str] = []
        field_scores: dict[str, float] = {}

        normalized_page = normalize_text(page_text)
        aic = normalize_aic(drug.aic)

        # AIC — identificatore più forte
        if aic and aic in re.sub(r"\D", "", page_text):
            score += self._config.weight_aic_match
            matched.append("aic")
            field_scores["aic"] = self._config.weight_aic_match
        elif aic and aic in page_url:
            score += self._config.weight_aic_match * 0.9
            matched.append("aic_url")
            field_scores["aic"] = self._config.weight_aic_match * 0.9
        else:
            rejected.append("AIC non presente nella pagina")

        # Nome farmaco — presenza token su pagina lunga, non solo overlap ratio
        name_norm = normalize_text(drug.name)
        name_tokens = set(tokenize(drug.name))
        page_token_set = set(tokenize(page_text))
        name_in_page = bool(name_norm and name_norm in normalize_text(page_text))
        all_name_tokens_present = bool(
            name_tokens and name_tokens <= page_token_set
        )
        name_ratio = token_overlap_ratio(drug.name, page_text)

        if name_in_page or all_name_tokens_present or name_ratio >= 0.85:
            score += self._config.weight_name_match
            matched.append("name")
            field_scores["name"] = self._config.weight_name_match
        elif name_ratio >= 0.55 or (name_tokens & page_token_set):
            score += self._config.weight_name_match * 0.5
            matched.append("name_partial")
            field_scores["name"] = self._config.weight_name_match * 0.5
            rejected.append("nome farmaco solo parzialmente corrispondente")
        else:
            score -= self._config.penalty_weak_name
            rejected.append("nome farmaco debole o assente")

        # Dosaggio
        dosage_cmp = compare_dosage(drug.dosage, page_text)
        field_scores["dosage"] = dosage_cmp.score * self._config.weight_dosage_match
        if dosage_cmp.level == MatchLevel.EXACT:
            score += self._config.weight_dosage_match
            matched.append("dosage")
        elif dosage_cmp.level == MatchLevel.PARTIAL:
            score += self._config.weight_dosage_match * 0.4
            matched.append("dosage_partial")
        elif dosage_cmp.level == MatchLevel.MISMATCH:
            score -= self._config.penalty_dosage_mismatch
            rejected.append(dosage_cmp.detail)

        # Forma farmaceutica
        form_cmp = compare_pharmaceutical_form(drug.pharmaceutical_form, page_text)
        field_scores["form"] = form_cmp.score * self._config.weight_form_match
        if form_cmp.level == MatchLevel.EXACT:
            score += self._config.weight_form_match
            matched.append("pharmaceutical_form")
        elif form_cmp.level in {MatchLevel.PARTIAL, MatchLevel.COMPATIBLE}:
            score += self._config.weight_form_match * 0.3
            matched.append("pharmaceutical_form_partial")
        elif form_cmp.level == MatchLevel.MISMATCH:
            score -= self._config.penalty_form_mismatch
            rejected.append(form_cmp.detail)

        # Quantità confezione
        qty_cmp = compare_quantity(drug.package_quantity, page_text)
        field_scores["quantity"] = qty_cmp.score * self._config.weight_quantity_match
        if qty_cmp.level == MatchLevel.EXACT:
            score += self._config.weight_quantity_match
            matched.append("package_quantity")
        elif qty_cmp.level == MatchLevel.PARTIAL:
            score += self._config.weight_quantity_match * 0.35
            matched.append("package_quantity_partial")
        elif qty_cmp.level == MatchLevel.MISMATCH:
            score -= self._config.penalty_quantity_mismatch
            rejected.append(qty_cmp.detail)

        # Azienda titolare
        if drug.marketing_authorization_holder:
            company_ratio = token_overlap_ratio(
                drug.marketing_authorization_holder, page_text
            )
            if company_ratio >= 0.6:
                score += self._config.weight_company_match
                matched.append("marketing_authorization_holder")
                field_scores["company"] = self._config.weight_company_match

        # Penalità pagina generica — non su schede prodotto trusted
        package_fields = {
            "dosage",
            "pharmaceutical_form",
            "package_quantity",
        }
        strong_package = (
            "name" in matched and len(package_fields & set(matched)) >= 3
        )
        is_product_page = any(
            hint in page_url for hint in ("/products/", "/prodotto/", "/product/")
        )

        if (
            _GENERIC_PAGE_HINTS.search(page_text)
            and "aic" not in matched
            and not (is_trusted_url(page_url) and (is_product_page or strong_package))
        ):
            score -= self._config.penalty_generic_page
            rejected.append("contenuto pagina generico/non prodotto")

        # Richiede almeno AIC o nome forte per considerare la pagina
        has_strong_identity = "aic" in matched or "name" in matched
        if not has_strong_identity:
            score *= 0.5
            rejected.append("manca identificazione forte del farmaco")

        return max(0.0, min(1.0, score)), matched, rejected, field_scores

    def _score_image(
        self, candidate: CandidateImage, drug: DrugInfo | None = None
    ) -> tuple[float, list[str]]:
        bonus = 0.0
        rejected: list[str] = []

        url_lower = candidate.image_url.lower()

        if any(
            bad in url_lower
            for bad in (
                "product-menu",
                "cosmetici",
                "menu-",
                "/menu/",
                "banner",
                "header",
                "sidebar",
                "nav-",
            )
        ):
            bonus -= 0.45
            rejected.append("immagine di menu/banner, non confezione")

        if candidate.extraction_method in {"meta_og_image", "json_ld"}:
            bonus += 0.15

        if candidate.metadata.get("product_hint"):
            bonus += 0.04

        if drug:
            name_token = normalize_text(drug.name).split()[0] if drug.name else ""
            alt_blob = normalize_text(f"{candidate.alt_text} {candidate.title}")
            if name_token and (
                name_token in url_lower or name_token in alt_blob
            ):
                bonus += 0.10

        width = candidate.width
        height = candidate.height
        if width is not None and height is not None:
            if (
                width < self._config.min_image_width
                or height < self._config.min_image_height
            ):
                bonus -= self._config.penalty_small_image
                rejected.append(
                    f"immagine piccola ({width}x{height})"
                )
            elif width >= 200 and height >= 200:
                bonus += 0.03

        alt_form_text = normalize_text(
            f"{candidate.alt_text} {candidate.title}"
        )
        if any(
            word in alt_form_text
            for word in ("logo", "icon", "banner", "social")
        ):
            bonus -= 0.15
            rejected.append("alt/title suggerisce immagine decorativa")

        return bonus, rejected


def select_best_match(
    page_matches: list[PageMatch],
    config: FetcherConfig,
) -> PageMatch | None:
    """Seleziona il miglior candidato solo se sopra soglia conservativa."""
    if not page_matches:
        return None

    ranked = sorted(
        page_matches,
        key=lambda m: (
            m.relevance_score,
            len(m.matched_fields),
            -len(m.rejected_reasons),
        ),
        reverse=True,
    )

    best = ranked[0]
    matched_set = set(best.matched_fields)
    has_aic = "aic" in matched_set or "aic_url" in matched_set
    has_strong_package = _has_strong_package_match(matched_set)

    required_score = (
        config.min_confidence_score
        if has_aic
        else config.min_confidence_package_match
        if has_strong_package
        else config.min_confidence_score
    )

    if best.relevance_score < required_score:
        return None

    # Vincolo aggiuntivo: serve AIC o match forte su nome + dettagli confezione
    has_package_details = (
        {"dosage", "pharmaceutical_form", "package_quantity"} & matched_set
    )
    has_strong_name = "name" in matched_set

    if not has_aic and not (has_strong_name and len(has_package_details) >= 2):
        return None

    # Penalità bloccante: mismatch espliciti su dosaggio/forma/quantità
    blocking = [
        r
        for r in best.rejected_reasons
        if any(
            kw in r.lower()
            for kw in (
                "dosaggio diverso",
                "forma diversa",
                "quantità diversa",
            )
        )
    ]
    if blocking:
        return None

    # Non accettare immagini da pagine di sola ricerca (troppo ambigue)
    if "/search" in best.source_page_url.lower():
        return None

    if best.candidates:
        img_url = best.candidates[0].image_url.lower()
        if any(
            bad in img_url
            for bad in ("product-menu", "cosmetici", "menu-", "placeholder")
        ):
            return None

    return best


def _has_strong_package_match(matched_fields: set[str]) -> bool:
    """Nome + dosaggio + forma + quantità tutti presenti (match esatto)."""
    required = {
        "name",
        "dosage",
        "pharmaceutical_form",
        "package_quantity",
    }
    return required <= matched_fields
