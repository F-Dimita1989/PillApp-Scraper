"""
Router FastAPI montabile nel backend PillApp.

Nel tuo main.py:
    from drug_image_fetcher.routes import router as drug_image_router
    app.include_router(drug_image_router, prefix="/api/v1")
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig

router = APIRouter(tags=["drug-images"])


class DrugImageRequest(BaseModel):
    aic: str = Field(..., min_length=9, max_length=12, description="Codice AIC a 9 cifre")


class DrugImageResponse(BaseModel):
    success: bool
    imageUrl: str | None = None
    sourcePageUrl: str | None = None
    message: str = ""


@router.post("/drugs/image", response_model=DrugImageResponse)
def get_drug_image(payload: DrugImageRequest) -> DrugImageResponse:
    result = fetch_drug_image(payload.aic, config=FetcherConfig.production())
    return DrugImageResponse(**result.to_dict())


@router.get("/drugs/image/health")
def drug_image_health() -> dict[str, Any]:
    config = FetcherConfig.production()
    return {
        "status": "ok",
        "googleCseEnabled": config.google_cse_enabled(),
    }
