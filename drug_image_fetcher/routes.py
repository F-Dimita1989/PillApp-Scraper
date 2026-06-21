"""
Router FastAPI montabile nel backend PillApp già su Render.

Nel tuo main.py esistente:

    from drug_image_fetcher.routes import router as drug_image_router
    app.include_router(drug_image_router, prefix="/api/v1")
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig
from drug_image_fetcher.models import DrugInfo, ImageFetchResult

router = APIRouter(tags=["drug-images"])


class DrugInfoPayload(BaseModel):
    aic: str = Field(..., min_length=9, max_length=12)
    name: str
    dosage: str | None = None
    pharmaceutical_form: str | None = None
    package_quantity: str | None = None
    marketing_authorization_holder: str | None = None
    active_substance: str | None = None


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
        return cls(**result.to_dict())


@router.post("/drugs/image", response_model=ImageFetchResponse)
def get_drug_image(payload: DrugInfoPayload) -> ImageFetchResponse:
    drug = DrugInfo(
        aic=payload.aic,
        name=payload.name,
        dosage=payload.dosage,
        pharmaceutical_form=payload.pharmaceutical_form,
        package_quantity=payload.package_quantity,
        marketing_authorization_holder=payload.marketing_authorization_holder,
        active_substance=payload.active_substance,
    )
    result = fetch_drug_image(drug, config=FetcherConfig.production())
    return ImageFetchResponse.from_result(result)


@router.get("/drugs/image/health")
def drug_image_health() -> dict[str, Any]:
    config = FetcherConfig.production()
    return {
        "status": "ok",
        "googleCseEnabled": config.google_cse_enabled(),
    }
