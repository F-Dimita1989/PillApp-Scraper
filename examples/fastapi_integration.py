"""
Esempio integrazione FastAPI — da copiare nel backend PillApp.

Avvio:
    pip install fastapi uvicorn
    uvicorn examples.fastapi_integration:app --reload

Il client mobile o il backend C# chiamano:
    POST /api/v1/drugs/image
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.models import DrugInfo, ImageFetchResult

app = FastAPI(title="PillApp Drug Image Service", version="0.1.0")


class DrugInfoPayload(BaseModel):
    aic: str = Field(..., min_length=9, max_length=12)
    name: str
    dosage: str | None = None
    pharmaceutical_form: str | None = None
    package_quantity: str | None = None
    marketing_authorization_holder: str | None = None


class ImageFetchResponse(BaseModel):
    success: bool
    image_url: str | None = Field(None, alias="imageUrl")
    source_page_url: str | None = Field(None, alias="sourcePageUrl")
    confidence_score: float = Field(0.0, alias="confidenceScore")
    matched_fields: list[str] = Field(default_factory=list, alias="matchedFields")
    rejected_reasons: list[str] = Field(default_factory=list, alias="rejectedReasons")
    message: str = ""

    model_config = {"populate_by_name": True}

    @classmethod
    def from_result(cls, result: ImageFetchResult) -> ImageFetchResponse:
        data = result.to_dict()
        return cls(**data)


@app.post("/api/v1/drugs/image", response_model=ImageFetchResponse)
def get_drug_image(payload: DrugInfoPayload) -> ImageFetchResponse:
    drug = DrugInfo(
        aic=payload.aic,
        name=payload.name,
        dosage=payload.dosage,
        pharmaceutical_form=payload.pharmaceutical_form,
        package_quantity=payload.package_quantity,
        marketing_authorization_holder=payload.marketing_authorization_holder,
    )
    result = fetch_drug_image(drug, config=FetcherConfig.production())
    return ImageFetchResponse.from_result(result)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}
