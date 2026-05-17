import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Projet Goutte d'eau – API de prévision de pluie",
    description=(
        "MVP de prévision de pluie pour les stations SYNOP d'Occitanie. "
        "Modèle XGBoost classifiant le risque de pluie significative (> 1 mm) à J+1."
    ),
    version="1.0.0",
    contact={"name": "France Météo / Projet Goutte d'eau"},
    license_info={"name": "MIT"},
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP local — restreindre en prod
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "goutte-d-eau-api",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
