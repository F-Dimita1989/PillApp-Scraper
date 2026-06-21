"""Test scoring e selezione best match."""

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.models import CandidateImage, DrugInfo, PageMatch
from drug_image_fetcher.scoring.scorer import PageScorer, select_best_match


SAMPLE_HTML_TEXT = (
    "AIC 027606012 Tachipirina 500 mg compresse rivestite "
    "confezione da 20 compresse Angelini Pharma"
)


def test_score_page_high_confidence() -> None:
    drug = DrugInfo(
        aic="027606012",
        name="Tachipirina",
        dosage="500 mg",
        pharmaceutical_form="compresse",
        package_quantity="20 compresse",
    )
    scorer = PageScorer(FetcherConfig())
    candidate = CandidateImage(
        image_url="https://example.com/tachipirina-500-20.jpg",
        source_page_url="https://example.com/prodotto",
        alt_text="Tachipirina 500 mg 20 compresse",
        width=400,
        height=400,
        extraction_method="meta_og_image",
    )

    matches = scorer.score_page(
        drug,
        "https://example.com/prodotto",
        SAMPLE_HTML_TEXT,
        [candidate],
    )

    assert matches[0].relevance_score >= 0.72
    assert "aic" in matches[0].matched_fields
    assert "dosage" in matches[0].matched_fields


def test_score_page_rejects_wrong_dosage() -> None:
    drug = DrugInfo(
        aic="027606012",
        name="Tachipirina",
        dosage="250 mg",
        pharmaceutical_form="compresse",
        package_quantity="20 compresse",
    )
    scorer = PageScorer(FetcherConfig())
    candidate = CandidateImage(
        image_url="https://example.com/img.jpg",
        source_page_url="https://example.com/p",
        width=300,
        height=300,
    )

    matches = scorer.score_page(
        drug,
        "https://example.com/p",
        SAMPLE_HTML_TEXT,
        [candidate],
    )

    assert any("dosaggio diverso" in r.lower() for r in matches[0].rejected_reasons)


def test_select_best_match_below_threshold_returns_none() -> None:
    config = FetcherConfig.conservative()
    weak = PageMatch(
        source_page_url="https://example.com",
        page_text="farmaco generico",
        candidates=[
            CandidateImage(
                image_url="https://example.com/logo.png",
                source_page_url="https://example.com",
            )
        ],
        relevance_score=0.3,
        matched_fields=["name_partial"],
    )
    assert select_best_match([weak], config) is None


def test_select_best_match_requires_package_evidence_without_aic() -> None:
    config = FetcherConfig(min_confidence_score=0.70)
    match = PageMatch(
        source_page_url="https://example.com",
        page_text="test",
        candidates=[
            CandidateImage(
                image_url="https://example.com/img.jpg",
                source_page_url="https://example.com",
                width=300,
                height=300,
            )
        ],
        relevance_score=0.75,
        matched_fields=["name", "dosage"],
    )
    # Solo nome+dosaggio senza AIC e senza 2 dettagli confezione → rifiutato
    assert select_best_match([match], config) is None
