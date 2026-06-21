"""
FastAPI app — entry point del microservizio Python su Render.

Avvio locale:
    uvicorn examples.fastapi_integration:app --reload --port 8000

Test:
    curl -X POST http://localhost:8000/api/v1/drugs/image \
         -H "Content-Type: application/json" \
         -d '{"aic": "048414104"}'
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from drug_image_fetcher.api import fetch_drug_image
from drug_image_fetcher.config import FetcherConfig

app = FastAPI(title="PillApp Drug Image Service", version="2.0.0")


class DrugImageRequest(BaseModel):
    aic: str = Field(..., min_length=9, max_length=12, description="Codice AIC a 9 cifre")
    name: str | None = Field(None, description="Nome commerciale opzionale")


class DrugImageResponse(BaseModel):
    success: bool
    imageUrl: str | None = None
    sourcePageUrl: str | None = None
    message: str = ""


@app.post("/api/v1/drugs/image", response_model=DrugImageResponse)
def get_drug_image(payload: DrugImageRequest) -> DrugImageResponse:
    result = fetch_drug_image(payload.aic, name=payload.name, config=FetcherConfig.production())
    return DrugImageResponse(**result.to_dict())


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}
