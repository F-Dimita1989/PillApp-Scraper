"""Drug image fetcher — recupero immagine confezione da codice AIC."""

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.models import ImageFetchResult

__all__ = ["fetch_drug_image", "FetcherConfig", "ImageFetchResult"]
__version__ = "2.0.0"
