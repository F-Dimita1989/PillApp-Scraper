"""
Esempio: montare drug_image_fetcher in un'app FastAPI già deployata su Render.

# backend/main.py (il tuo file esistente)

from fastapi import FastAPI
from drug_image_fetcher.routes import router as drug_image_router

app = FastAPI(title="PillApp API")

# ... le tue route esistenti (auth, terapie, ecc.) ...

app.include_router(drug_image_router, prefix="/api/v1")

# Avvio locale (Render usa il comando start del dashboard)
# uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

from fastapi import FastAPI

from drug_image_fetcher.routes import router as drug_image_router

app = FastAPI(title="PillApp API — esempio mount")

app.include_router(drug_image_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
