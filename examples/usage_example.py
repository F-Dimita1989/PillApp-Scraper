"""
Esempio di utilizzo reale del modulo drug_image_fetcher.

Eseguire dalla root del progetto:
    python -m examples.usage_example

Configurazione Google CSE (opzionale, per copertura estesa):
    set GOOGLE_CSE_API_KEY=your_key
    set GOOGLE_CSE_ENGINE_ID=your_cx_id

Creare il motore CSE su https://programmablesearchengine.google.com/
includendo i domini in drug_image_fetcher/search/trusted_sites.py
"""

from __future__ import annotations

import json
import logging

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.logging_config import setup_logging
from drug_image_fetcher.models import DrugInfo

DRUG = DrugInfo(
    aic="027606012",
    name="Tachipirina",
    dosage="500 mg",
    pharmaceutical_form="compresse",
    package_quantity="20 compresse",
    marketing_authorization_holder="Angelini Pharma S.p.A.",
)


def main() -> None:
    setup_logging(logging.INFO)

    # Produzione: conservativo + credenziali da env (se presenti)
    config = FetcherConfig.production()

    result = fetch_drug_image(DRUG, config=config)

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    if result.success:
        print(f"\nImmagine affidabile: {result.image_url}")
        print(f"  Confidenza: {result.confidence_score:.2%}")
        print(f"  Campi matched: {', '.join(result.matched_fields)}")
    else:
        print(f"\n{result.message}")
        if result.rejected_reasons:
            print("  Motivi:")
            for reason in result.rejected_reasons:
                print(f"    - {reason}")


if __name__ == "__main__":
    main()
