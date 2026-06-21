"""Drug image fetcher: recupero affidabile di immagini confezione da codice AIC."""

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.models import (
    CandidateImage,
    DrugInfo,
    ImageFetchResult,
    PageMatch,
)

__all__ = [
    "CandidateImage",
    "DrugInfo",
    "FetcherConfig",
    "ImageFetchResult",
    "PageMatch",
    "fetch_drug_image",
]

__version__ = "0.1.0"
