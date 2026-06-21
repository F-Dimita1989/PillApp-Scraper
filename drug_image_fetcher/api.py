"""API pubblica del modulo — punto di integrazione backend."""

from __future__ import annotations

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.engine import DrugImageEngine
from drug_image_fetcher.models import DrugInfo, ImageFetchResult
from drug_image_fetcher.search.providers import SearchProvider


def fetch_drug_image(
    drug: DrugInfo,
    *,
    config: FetcherConfig | None = None,
    search_provider: SearchProvider | None = None,
) -> ImageFetchResult:
    """
    Funzione principale per il backend PillApp.

    Esempio integrazione FastAPI:
        @app.post("/api/drugs/image")
        def get_drug_image(payload: DrugInfoPayload) -> dict:
            drug = DrugInfo(**payload.model_dump())
            result = fetch_drug_image(drug, config=FetcherConfig.conservative())
            return result.to_dict()

    Esempio integrazione C# (chiamata HTTP al servizio Python):
        var response = await httpClient.PostAsJsonAsync("/api/drugs/image", drugInfo);
        var result = await response.Content.ReadFromJsonAsync<ImageFetchResultDto>();
    """
    engine = DrugImageEngine(
        config=config or FetcherConfig.production(),
        search_provider=search_provider,
    )
    return engine.fetch(drug)
