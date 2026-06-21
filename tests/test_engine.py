"""Test integrazione engine con provider statico (nessuna rete)."""

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.engine import DrugImageEngine
from drug_image_fetcher.models import DrugInfo
from drug_image_fetcher.search.providers import StaticUrlListProvider

PRODUCT_PAGE = """
<html><head>
<meta property="og:image" content="https://cdn.example.com/aic-027606012.jpg" />
</head><body>
<h1>Tachipirina 500 mg compresse</h1>
<p>AIC 027606012 - Confezione da 20 compresse rivestite</p>
<img class="product" src="https://cdn.example.com/aic-027606012.jpg"
     width="400" height="400" alt="Tachipirina 500 mg 20 compresse" />
</body></html>
"""

WRONG_PRODUCT_PAGE = """
<html><body>
<h1>Tachipirina 500 mg</h1>
<p>Confezione da 10 compresse - AIC 999999999</p>
<img src="https://cdn.example.com/wrong.jpg" width="400" height="400" />
</body></html>
"""


class FakeHttpClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages

    def get(self, url: str) -> str | None:
        return self._pages.get(url)


def test_engine_finds_reliable_image() -> None:
    drug = DrugInfo(
        aic="027606012",
        name="Tachipirina",
        dosage="500 mg",
        pharmaceutical_form="compresse",
        package_quantity="20 compresse",
    )
    page_url = "https://farmacia.example.com/tachipirina-500-20"
    engine = DrugImageEngine(
        config=FetcherConfig(enable_cache=False, min_confidence_score=0.72),
        search_provider=StaticUrlListProvider([page_url]),
        http_client=FakeHttpClient({page_url: PRODUCT_PAGE}),
    )

    result = engine.fetch(drug)

    assert result.success is True
    assert result.image_url == "https://cdn.example.com/aic-027606012.jpg"
    assert result.confidence_score >= 0.72
    assert "aic" in result.matched_fields


def test_engine_rejects_unreliable_match() -> None:
    drug = DrugInfo(
        aic="027606012",
        name="Tachipirina",
        dosage="500 mg",
        pharmaceutical_form="compresse",
        package_quantity="20 compresse",
    )
    page_url = "https://farmacia.example.com/wrong"
    engine = DrugImageEngine(
        config=FetcherConfig.conservative(),
        search_provider=StaticUrlListProvider([page_url]),
        http_client=FakeHttpClient({page_url: WRONG_PRODUCT_PAGE}),
    )

    result = engine.fetch(drug)

    assert result.success is False
    assert result.image_url is None
    assert "affidabile" in result.message.lower()
