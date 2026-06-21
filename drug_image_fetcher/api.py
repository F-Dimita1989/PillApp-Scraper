"""API pubblica — integrazione backend PillApp."""

from __future__ import annotations

from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.engine import fetch_image_by_aic
from drug_image_fetcher.models import ImageFetchResult


def fetch_drug_image(
    aic: str,
    name: str | None = None,
    config: FetcherConfig | None = None,
) -> ImageFetchResult:
    """
    Dato un codice AIC (e opzionalmente il nome commerciale), restituisce
    l'immagine della confezione.

    L'AIC è obbligatorio ed è la fonte di verità: ogni pagina trovata viene
    accettata solo se contiene quell'AIC nel testo o nell'URL.

    Esempio:
        result = fetch_drug_image("048414104", name="Oki")
        if result.success:
            print(result.image_url)
    """
    return fetch_image_by_aic(aic, name=name, config=config)
