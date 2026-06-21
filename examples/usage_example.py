"""
Esempio di utilizzo del modulo drug_image_fetcher.

Eseguire dalla root del progetto:
    python -m examples.usage_example

Configurazione Google CSE (opzionale, migliora la copertura):
    set GOOGLE_CSE_API_KEY=your_key
    set GOOGLE_CSE_ENGINE_ID=your_cx_id
"""

from __future__ import annotations

import json
import logging

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.logging_config import setup_logging


def main() -> None:
    setup_logging(logging.INFO)
    config = FetcherConfig.production()

    # Passa solo AIC (obbligatorio) + name (opzionale, migliora la ricerca)
    result = fetch_drug_image("048414104", name="Oki", config=config)

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    if result.success:
        print(f"\nImmagine trovata: {result.image_url}")
    else:
        print(f"\n{result.message}")


if __name__ == "__main__":
    main()
