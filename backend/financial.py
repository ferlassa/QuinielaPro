"""
Financial Agent — Análisis Económico y ROI
Implementa:
  - Esperanza Matemática por columna: E[X] = P(ganar)·Premio − P(perder)·Coste
  - Criterio de Kelly para dimensionar apuesta
  - Panel de ROI histórico (últimas 10 y 60 jornadas)
  - Backtesting automatizado sobre historial de predicciones
"""

import os
from typing import List, Dict
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Jornada, Prediction, Match

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./quiniela.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


# ─────────────────────────────────────────────────────────────────────────────
# ESPERANZA MATEMÁTICA
# ─────────────────────────────────────────────────────────────────────────────

def expected_value(
    prob_win: float,
    prize: float,
    cost_per_column: float
) -> float:
    """
    Calcula la Esperanza Matemática de una apuesta.
    E[X] = P(ganar) × Premio − P(perder) × Coste

    Args:
        prob_win: Probabilidad de acertar (combinatoria × ML).
        prize:    Premio estimado si se gana (€).
        cost_per_column: Coste de cada columna (€0.60 por defecto en Quiniela).

    Returns:
        Valor esperado en euros.
    """
    prob_lose = 1.0 - prob_win
    ev = (prob_win * prize) - (prob_lose * cost_per_column)
    return round(ev, 4)


# ─────────────────────────────────────────────────────────────────────────────
# CRITERIO DE KELLY
# ─────────────────────────────────────────────────────────────────────────────

def kelly_criterion(
    prob_win: float,
    decimal_odds: float,
    bankroll: float,
    fraction: float = 0.25      # Kelly fraccional (más conservador)
) -> Dict:
    """
    Calcula la fracción óptima del bankroll a apostar según Kelly.
    f* = (bp − q) / b  → luego aplica Kelly fraccional.

    Args:
        prob_win:      Probabilidad estimada de ganar.
        decimal_odds:  Cuotas decimales (equivalente al ratio Premio/Coste).
        bankroll:      Capital disponible en euros.
        fraction:      Factor de conservadurismo (0.25 = Kelly cuarto).

    Returns:
        Diccionario con edge, f_star, apuesta_sugerida y clasificación de riesgo.
    """
    b = decimal_odds - 1.0
    q = 1.0 - prob_win
    edge = (b * prob_win) - q

    if edge <= 0:
        return {
            "edge": round(edge, 4),
            "f_star_full": 0.0,
            "f_star_frac": 0.0,
            "apuesta_euros": 0.0,
            "riesgo": "NO APOSTAR — Edge negativo"
        }

    f_star = edge / b          # Kelly completo
    f_frac  = f_star * fraction # Kelly fraccional
    apuesta  = round(f_frac * bankroll, 2)

    riesgo = (
        "BAJO" if f_frac < 0.05 else
        "MODERADO" if f_frac < 0.15 else
        "ALTO"
    )

    return {
        "edge":          round(edge, 4),
        "f_star_full":   round(f_star, 4),
        "f_star_frac":   round(f_frac, 4),
        "apuesta_euros": apuesta,
        "riesgo":        riesgo
    }


# ─────────────────────────────────────────────────────────────────────────────
# PANEL DE ROI HISTÓRICO — Backtesting
# ─────────────────────────────────────────────────────────────────────────────

class ROIBacktester:
    """
    Compara las predicciones del modelo ML contra los resultados reales
    para calcular el ROI de la estrategia en distintos períodos.
    """

    COST_PER_COLUMN = 0.60      # €/columna (precio oficial Quiniela)
    PRIZES = {                  # Premios aprox. por categoría
        15: 800_000, 14: 40_000, 13: 2_000,
        12: 150,    11: 30,      10: 10
    }

    def __init__(self, cost_per_column: float = 0.60):
        self.cost_per_column = cost_per_column

    def simulate_jornada(
        self,
        predictions: List[str],   # Signos predichos para los 14 partidos
        results: List[str],        # Signos reales
        n_columns: int = 1
    ) -> Dict:
        """
        Simula el resultado de una jornada dado un set de predicciones.
        """
        aciertos = sum(p == r for p, r in zip(predictions, results))
        coste    = n_columns * self.cost_per_column
        premio   = self.PRIZES.get(aciertos, 0)

        return {
            "aciertos": aciertos,
            "coste":    round(coste, 2),
            "premio":   premio,
            "profit":   round(premio - coste, 2)
        }

    def backtest(
        self,
        history: List[Dict],   # Lista de resultados de simulate_jornada
        period: int = 10
    ) -> Dict:
        """
        Calcula el ROI sobre las últimas `period` jornadas.
        """
        subset   = history[-period:]
        invested = sum(j["coste"]   for j in subset)
        returned = sum(j["premio"]  for j in subset)
        profit   = returned - invested
        roi      = (profit / invested * 100) if invested > 0 else 0.0

        return {
            "periodo":    period,
            "jornadas":   len(subset),
            "invertido":  round(invested, 2),
            "recuperado": round(returned, 2),
            "beneficio":  round(profit, 2),
            "roi_%":      round(roi, 2),
            "aciertos_medios": round(
                sum(j["aciertos"] for j in subset) / max(len(subset), 1), 2
            )
        }


# ─────────────────────────────────────────────────────────────────────────────
# DEMO / CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random

    print("=" * 50)
    print("ESPERANZA MATEMÁTICA")
    print("=" * 50)
    ev = expected_value(prob_win=0.0015, prize=800_000, cost_per_column=0.60)
    print(f"  Pleno 15: E[X] = {ev} €")

    ev14 = expected_value(prob_win=0.025, prize=40_000, cost_per_column=0.60)
    print(f"  14 aciertos: E[X] = {ev14} €")

    print("\n" + "=" * 50)
    print("CRITERIO DE KELLY")
    print("=" * 50)
    kelly = kelly_criterion(
        prob_win=0.025,
        decimal_odds=40_000 / 0.60,
        bankroll=500.0,
        fraction=0.25
    )
    for k, v in kelly.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 50)
    print("BACKTESTING ROI — 10 y 60 Jornadas")
    print("=" * 50)

    backtester = ROIBacktester()
    signos = ["1", "X", "2"]

    history = []
    for _ in range(60):
        preds   = [random.choice(signos) for _ in range(14)]
        results = [random.choice(signos) for _ in range(14)]
        history.append(backtester.simulate_jornada(preds, results, n_columns=6))

    for periodo in [10, 60]:
        roi_data = backtester.backtest(history, period=periodo)
        print(f"\n  Últimas {periodo} jornadas:")
        for k, v in roi_data.items():
            print(f"    {k}: {v}")
