"""
Quiniela Predictor Pro — FastAPI Backend
Endpoints RESTful que conectan todos los módulos:
  - /predict          → Motor ML (PCA + Logit + Poisson)
  - /optimize         → Optimizador (R1-R6, Megaquin, Hamming, .qui export)
  - /kelly            → Criterio de Kelly
  - /roi              → Backtesting ROI (10 y 60 jornadas)
  - /jornadas         → Lecturas de la BD
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import random
import json
import threading
from scraper import init_data

# Local modules
from ml_engine import MLEngine
from optimizer import (
    generate_columns_from_reduction,
    MegaquinFilter,
    reduce_by_hamming,
    export_columns,
    REDUCTIONS
)
from financial import expected_value, kelly_criterion, ROIBacktester
from models import Match, Jornada, Season
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./quiniela.db")
# Railway PostgreSQL uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine_db = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine_db)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# ─────────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Quiniela Predictor Pro API",
    description="Motor estadístico avanzado para La Quiniela española",
    version="1.0.0"
)

# HEALTHCHECK FIRST: Responder inmediatamente para pasar el despliegue de Railway
@app.get("/health", tags=["Info"])
def health():
    return {"status": "ok"}

@app.get("/", tags=["Info"])
def root():
    return {"status": "ok", "message": "Quiniela Predictor Pro API v1.0"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "healthcheck.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia global del motor ML (se entrena al arrancar)
ml = MLEngine()

@app.on_event("startup")
def startup_event():
    """Arranca el servidor instantáneamente y lanza tareas en segundo plano."""

    def background_init():
        import asyncio as _aio
        try:
            _aio.run(init_data())
            print("BD inicializada.")
        except Exception as e:
            print(f"Carga de datos omitida: {e}")
        try:
            ml.train()
            print("Motor ML listo.")
        except Exception as e:
            print(f"Entrenamiento ML omitido (sin datos aún): {e}")

    t = threading.Thread(target=background_init, daemon=True)
    t.start()


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class MatchInput(BaseModel):
    home_elo: float = Field(1500, description="ELO del equipo local")
    away_elo: float = Field(1500, description="ELO del equipo visitante")
    home_xg: float = Field(1.2, description="xG esperados local")
    away_xg: float = Field(0.9, description="xG esperados visitante")

class JornadaInput(BaseModel):
    matches: List[MatchInput] = Field(..., max_items=14, min_items=14,
        description="Lista de 14 partidos de la jornada")

class OptimizeRequest(BaseModel):
    jornada: JornadaInput
    reduction: str = Field("R1", description="Reducción a aplicar: R1-R6")
    max_variantes_x2: int = Field(9, ge=0, le=14)
    min_sign1: int = Field(2, ge=0, le=14)
    max_racha: int = Field(5, ge=1, le=14)
    max_interrupciones: int = Field(10, ge=0, le=14)
    hamming_distance: int = Field(2, ge=1, le=14)
    target_columns: int = Field(10, ge=1, le=50)

class KellyRequest(BaseModel):
    prob_win: float = Field(..., ge=0.0, le=1.0)
    prize_euros: float = Field(..., gt=0)
    cost_per_column: float = Field(0.60, gt=0)
    bankroll: float = Field(100.0, gt=0)
    kelly_fraction: float = Field(0.25, ge=0.01, le=1.0)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# Endpoints de salud movidos al inicio


@app.post("/predict", tags=["Motor ML"])
def predict_jornada(jornada: JornadaInput):
    """
    Predice las probabilidades 1X2 para los 14 partidos de una jornada
    y el resultado más probable del Pleno al 15 (Poisson).
    """
    results = []
    for i, m in enumerate(jornada.matches):
        try:
            probs = ml.predict_match(m.home_elo, m.away_elo, m.home_xg, m.away_xg)
        except Exception:
            # Si aún no hay modelo entrenado, devolver distribución uniforme
            probs = {"1": 0.45, "X": 0.28, "2": 0.27}

        p15_result, p15_prob = ml.predict_poisson_p15(m.home_xg, m.away_xg)

        results.append({
            "partido": i + 1,
            "prob_1": round(probs["1"], 3),
            "prob_X": round(probs["X"], 3),
            "prob_2": round(probs["2"], 3),
            "signo_mas_probable": max(probs, key=probs.get),
            "pleno15_resultado": p15_result,
            "pleno15_prob": round(p15_prob, 4)
        })

    return {"jornada": results}


@app.post("/optimize", tags=["Optimizador"])
def optimize_columns(req: OptimizeRequest):
    """
    Genera columnas optimizadas para la jornada usando la reducción seleccionada,
    aplica filtros Megaquin y diversificación por distancia de Hamming.
    """
    if req.reduction not in REDUCTIONS:
        raise HTTPException(400, detail=f"Reducción '{req.reduction}' no válida. Usa R1-R6.")

    # Construir predicciones ordenadas por probabilidad descendente
    predictions = []
    for i, m in enumerate(req.jornada.matches):
        try:
            probs = ml.predict_match(m.home_elo, m.away_elo, m.home_xg, m.away_xg)
        except Exception:
            probs = {"1": 0.45, "X": 0.28, "2": 0.27}

        ordered = sorted(probs, key=probs.get, reverse=True)  # e.g. ["1","X","2"]
        predictions.append((f"Partido_{i+1}", ordered))

    # Generar reducción
    columns = generate_columns_from_reduction(predictions, req.reduction)

    # Filtros Megaquin
    mf = MegaquinFilter(
        max_variantes_x2=req.max_variantes_x2,
        min_sign1=req.min_sign1,
        max_racha_mismo_signo=req.max_racha,
        max_interrupciones=req.max_interrupciones
    )
    filtered = mf.filtrar(columns)

    # Hamming
    diversas = reduce_by_hamming(
        filtered,
        min_distance=req.hamming_distance,
        target_columns=req.target_columns
    )

    # Exportar
    filepath = "ultima_apuesta.qui"
    export_columns(diversas, filepath)

    return {
        "reduccion": req.reduction,
        "garantia_aciertos": REDUCTIONS[req.reduction]["garantia_aciertos"],
        "columnas_generadas": len(columns),
        "columnas_filtradas_megaquin": len(filtered),
        "columnas_finales": len(diversas),
        "columnas": [" ".join(c) for c in diversas],
        "archivo_qui": filepath
    }


@app.post("/kelly", tags=["Análisis Financiero"])
def calcular_kelly(req: KellyRequest):
    """
    Aplica el Criterio de Kelly para determinar el tamaño óptimo de apuesta.
    """
    decimal_odds = req.prize_euros / req.cost_per_column
    ev = expected_value(req.prob_win, req.prize_euros, req.cost_per_column)
    k = kelly_criterion(req.prob_win, decimal_odds, req.bankroll, req.kelly_fraction)
    return {
        "esperanza_matematica": ev,
        **k
    }


@app.get("/roi", tags=["Análisis Financiero"])
def calcular_roi(periodo: int = Query(10, ge=1, le=100)):
    """
    Simula un backtesting de ROI sobre las últimas `periodo` jornadas
    usando las predicciones del modelo ML vs resultados reales de la BD.
    """
    db = SessionLocal()
    matches = db.query(Match).order_by(Match.id.desc()).limit(periodo * 14).all()
    db.close()

    if not matches:
        return {"error": "Sin datos en la BD para calcular ROI"}

    backtester = ROIBacktester()
    history = []
    for i in range(0, len(matches) - 14, 14):
        jornada_matches = matches[i:i + 14]
        preds = []
        reals = []
        for m in jornada_matches:
            try:
                probs = ml.predict_match(
                    m.elo_home or 1500, m.elo_away or 1500,
                    m.xg_home or 1.2, m.xg_away or 0.9
                )
                preds.append(max(probs, key=probs.get))
            except Exception:
                preds.append(random.choice(["1", "X", "2"]))
            reals.append(m.sign or "1")

        history.append(backtester.simulate_jornada(preds, reals, n_columns=6))

    return backtester.backtest(history, period=min(periodo, len(history)))


@app.get("/jornadas", tags=["Datos"])
def get_jornadas(limit: int = Query(10, ge=1, le=100)):
    """Devuelve las últimas N jornadas guardadas en la BD."""
    db = SessionLocal()
    jornadas = db.query(Jornada).order_by(Jornada.id.desc()).limit(limit).all()
    db.close()
    return [{"id": j.id, "numero": j.number, "fecha": str(j.date)} for j in jornadas]


@app.get("/download-qui", tags=["Exportación"])
def download_qui():
    """Descarga el último archivo .qui generado."""
    import os
    filepath = "ultima_apuesta.qui"
    if not os.path.exists(filepath):
        raise HTTPException(404, detail="No hay archivo .qui generado. Ejecuta el optimizador primero.")
    return FileResponse(filepath, media_type="text/plain", filename="quiniela_apuesta.qui")
