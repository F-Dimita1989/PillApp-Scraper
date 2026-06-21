"""Test generazione query di ricerca."""

from drug_image_fetcher.models import DrugInfo
from drug_image_fetcher.search.queries import build_search_queries


def test_build_search_queries_ordered_by_specificity() -> None:
    drug = DrugInfo(
        aic="027606012",
        name="Tachipirina",
        dosage="500 mg",
        pharmaceutical_form="compresse",
        package_quantity="20 compresse",
        marketing_authorization_holder="Angelini Pharma",
    )
    queries = build_search_queries(drug, max_queries=4)

    assert len(queries) >= 2
    assert "027606012" in queries[0]
    assert "confezione" in queries[0].lower()
    assert queries[0].count("Tachipirina") == 1


def test_build_search_queries_deduplication() -> None:
    drug = DrugInfo(aic="027606012", name="Tachipirina")
    queries = build_search_queries(drug, max_queries=10)
    assert len(queries) == len(set(q.lower() for q in queries))
