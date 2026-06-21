"""Test stack provider produzione."""

from unittest.mock import MagicMock, patch

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.models import DrugInfo
from drug_image_fetcher.search.providers import (
    GoogleCustomSearchProvider,
    ManufacturerSiteProvider,
    TrustedPharmacySearchProvider,
    build_production_providers,
)


def test_trusted_pharmacy_provider_returns_whitelist_urls() -> None:
    config = FetcherConfig(enable_trusted_pharmacy_search=True)
    provider = TrustedPharmacySearchProvider(config)
    results = provider.search("Tachipirina 500 mg", max_results=3)

    assert len(results) >= 1
    assert all("/search?q=" in r.url for r in results)


def test_manufacturer_provider_angelini() -> None:
    drug = DrugInfo(
        aic="027606012",
        name="Tachipirina",
        marketing_authorization_holder="Angelini Pharma",
    )
    results = ManufacturerSiteProvider(drug).search("Tachipirina 500", max_results=1)

    assert len(results) == 1
    assert "angelini.it" in results[0].url


def test_build_production_providers_chain() -> None:
    drug = DrugInfo(
        aic="027606012",
        name="Tachipirina",
        marketing_authorization_holder="Angelini Pharma",
    )
    config = FetcherConfig.conservative()
    composite = build_production_providers(
        drug, config, http_get=lambda url: None
    )

    results = composite.search("027606012 Tachipirina", max_results=10)
    providers_used = {r.provider for r in results}

    assert "aifa_direct" in providers_used
    assert "manufacturer_site" in providers_used


@patch("drug_image_fetcher.search.providers.requests.Session")
def test_google_cse_filters_untrusted_domains(mock_session_cls: MagicMock) -> None:
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "link": "https://www.farmaciaigea.com/prodotto/tachipirina",
                "title": "Tachipirina",
                "snippet": "500 mg",
            },
            {
                "link": "https://untrusted-spam.example/drug",
                "title": "Spam",
                "snippet": "",
            },
        ]
    }
    mock_session.get.return_value = mock_response

    config = FetcherConfig(
        google_cse_api_key="test-key",
        google_cse_engine_id="test-cx",
    )
    provider = GoogleCustomSearchProvider(config)
    results = provider.search("Tachipirina 500 mg", max_results=5)

    assert len(results) == 1
    assert "farmaciaigea.com" in results[0].url
