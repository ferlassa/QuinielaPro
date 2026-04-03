"""
Senior Betting Specialist - Optimizador de Columnas Quiniela
Implementa:
  - Reducciones R1-R6 (oficiales SELAE)
  - Sistemas por distancia de Hamming
  - Filtros de Megaquin (variantes, interrupciones, secuencias)
  - Exportación .qui / .txt
"""

import itertools
from typing import List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# DEFINICIONES DE REDUCCIONES OFICIALES (R1 a R6)
# Cada reducción se define por:
#   triples  → número de partidos con 3 signos marcados (1, X, 2)
#   dobles   → número de partidos con 2 signos marcados
# El resto se juega a un signo fijo (pronóstico más probable del ML)
# ─────────────────────────────────────────────────────────────────────────────

REDUCTIONS = {
    "R1": {"triples": 4, "dobles": 0, "garantia_aciertos": 13},
    "R2": {"triples": 3, "dobles": 2, "garantia_aciertos": 13},
    "R3": {"triples": 2, "dobles": 4, "garantia_aciertos": 13},
    "R4": {"triples": 3, "dobles": 1, "garantia_aciertos": 12},
    "R5": {"triples": 2, "dobles": 3, "garantia_aciertos": 12},
    "R6": {"triples": 0, "dobles": 6, "garantia_aciertos": 12},
}


def generate_columns_from_reduction(
    predictions: List[Tuple[str, List[str]]],
    reduction_key: str
) -> List[List[str]]:
    """
    Genera un sistema reducido a partir de las predicciones del motor ML.

    Args:
        predictions: Lista de 14 tuplas [(partido, [signos_ordenados_por_prob])].
                     Ejemplo: [("RM-BAR", ["1", "X", "2"]), ...]
        reduction_key: "R1" a "R6"

    Returns:
        Lista de columnas (cada columna = lista de 14 signos).
    """
    if len(predictions) != 14:
        raise ValueError(f"Se esperan 14 partidos, se recibieron {len(predictions)}")

    r = REDUCTIONS[reduction_key]
    n_triples = r["triples"]
    n_dobles = r["dobles"]
    n_singles = 14 - n_triples - n_dobles
    garantia = r["garantia_aciertos"]

    # Ordenar partidos por incertidumbre (más signos = más incierto)
    indexed = [(i, pred[0], pred[1]) for i, pred in enumerate(predictions)]
    indexed.sort(key=lambda x: len(x[2]), reverse=True)

    # Asignar profundidad 3/2/1 a cada partido
    partidos_triple = [indexed[i] for i in range(n_triples)]
    partidos_doble  = [indexed[i] for i in range(n_triples, n_triples + n_dobles)]
    partidos_single = [indexed[i] for i in range(n_triples + n_dobles, 14)]

    # Producir el cartesiano de las variantes
    variantes_triple = [list(itertools.islice(p[2], 3)) for p in partidos_triple]
    variantes_doble  = [list(itertools.islice(p[2], 2)) for p in partidos_doble]
    variantes_single = [[p[2][0]] for p in partidos_single]

    all_variantes = variantes_triple + variantes_doble + variantes_single
    all_indices   = [p[0] for p in partidos_triple + partidos_doble + partidos_single]

    columnas_raw = list(itertools.product(*all_variantes))

    # Reconstruir orden original (índice 0-13)
    columns = []
    for col in columnas_raw:
        row = [""] * 14
        for pos, idx in enumerate(all_indices):
            row[idx] = col[pos]
        columns.append(row)

    print(f"[{reduction_key}] Generadas {len(columns)} columnas — garantía mínima: {garantia} aciertos")
    return columns


# ─────────────────────────────────────────────────────────────────────────────
# FILTROS MEGAQUIN
# ─────────────────────────────────────────────────────────────────────────────

class MegaquinFilter:
    """
    Implementa los filtros de calidad avanzados estilo Megaquin.
    """

    def __init__(
        self,
        max_variantes_x2: int = 12,         # maximo de resultados X o 2
        min_sign1: int = 1,                  # minimo de signos '1'
        max_racha_mismo_signo: int = 6,      # sin mas de N signos iguales seguidos
        max_interrupciones: int = 14,        # cambios de signo permitidos (ver Megaquin)
    ):
        self.max_variantes_x2     = max_variantes_x2
        self.min_sign1            = min_sign1
        self.max_racha            = max_racha_mismo_signo
        self.max_interrupciones   = max_interrupciones

    def cumple_variantes(self, col: List[str]) -> bool:
        """Rechaza columnas con demasiadas X o 2 (baja probabilidad estadística)."""
        count_x2 = sum(1 for s in col if s in ("X", "2"))
        return count_x2 <= self.max_variantes_x2

    def cumple_minimo_1(self, col: List[str]) -> bool:
        """Requiere al menos N signos '1' (1 es estadísticamente el más frecuente)."""
        return col.count("1") >= self.min_sign1

    def cumple_racha(self, col: List[str]) -> bool:
        """No permite más de N signos iguales consecutivos."""
        max_run = 1
        run = 1
        for i in range(1, len(col)):
            if col[i] == col[i - 1]:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 1
        return max_run <= self.max_racha

    def cumple_interrupciones(self, col: List[str]) -> bool:
        """Limita el número de cambios abruptos de signo (interrupciones)."""
        interrupciones = sum(1 for i in range(1, len(col)) if col[i] != col[i - 1])
        return interrupciones <= self.max_interrupciones

    def filtrar(self, columns: List[List[str]]) -> List[List[str]]:
        """Aplica todos los filtros Megaquin a un conjunto de columnas."""
        antes = len(columns)
        columns = [c for c in columns if self.cumple_variantes(c)]
        columns = [c for c in columns if self.cumple_minimo_1(c)]
        columns = [c for c in columns if self.cumple_racha(c)]
        columns = [c for c in columns if self.cumple_interrupciones(c)]
        print(f"[Megaquin] {len(columns)}/{antes} columnas superaron los filtros.")
        return columns


# ─────────────────────────────────────────────────────────────────────────────
# DISTANCIA DE HAMMING — Sistemas reducidos personalizados
# ─────────────────────────────────────────────────────────────────────────────

def hamming_distance(col_a: List[str], col_b: List[str]) -> int:
    """Calcula la distancia de Hamming entre dos columnas."""
    return sum(a != b for a, b in zip(col_a, col_b))


def reduce_by_hamming(
    columns: List[List[str]],
    min_distance: int = 2,
    target_columns: int = 10
) -> List[List[str]]:
    """
    Selecciona un subconjunto diverso de columnas garantizando
    que cualquier par tenga al menos `min_distance` diferencias (Hamming).
    """
    selected = []
    for col in columns:
        if all(hamming_distance(col, s) >= min_distance for s in selected):
            selected.append(col)
            if len(selected) >= target_columns:
                break
    print(f"[Hamming d>={min_distance}] Seleccionadas {len(selected)} columnas diversas.")
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def export_columns(columns: List[List[str]], p15: str = "1-1", filepath: str = "apuesta.qui") -> str:
    """
    Exporta las columnas en formato compatible con validadores oficiales.
    Añade el Pleno al 15 al final de cada columna.
    """
    # Formato P15 oficial: 0, 1, 2, M
    # Si recibimos "1-1" -> 1 1
    # Si recibimos "M-0" -> M 0
    p15_parts = p15.replace("-", " ").split()
    p15_str = "".join(p15_parts) if len(p15_parts) == 2 else "11"

    lines = []
    for col in columns:
        # 14 signos + 2 del P15
        lines.append("".join(col) + p15_str)
    
    content = "\n".join(lines)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[Export] {len(columns)} apuestas guardadas en: {filepath}")
    return content

def propose_strategies(predictions: List[dict]):
    """
    Analiza predicciones y propone 3 estrategias (R1, R2, R6).
    """
    def get_ordered_signs(p):
        return sorted(['1', 'X', '2'], key=lambda s: p.get(s, 0), reverse=True)

    ordered_preds = []
    for p in predictions[:14]:
        ordered_preds.append((f"{p['home']}-{p['away']}", get_ordered_signs(p)))

    # R6: 6 Dobles (64 apuestas) -> 32€
    cols_r6 = generate_columns_from_reduction(ordered_preds, "R6")
    # R2: 3 Triples + 2 Dobles (108 apuestas) -> 54€
    cols_r2 = generate_columns_from_reduction(ordered_preds, "R2")
    # R1: 4 Triples (81 apuestas) -> 40.5€
    cols_r1 = generate_columns_from_reduction(ordered_preds, "R1")

    return [
        {"id": 1, "name": "🛡️ Conservadora (R6)", "desc": "6 Dobles. Ideal para asegurar premios menores.", "cost": 32.0, "cols": cols_r6},
        {"id": 2, "name": "⚖️ Equilibrada (R2)", "desc": "3 Triples + 2 Dobles. Balance entre coste y riesgo.", "cost": 54.0, "cols": cols_r2},
        {"id": 3, "name": "🔥 Agresiva (R1)", "desc": "4 Triples. Máxima cobertura ante sorpresas.", "cost": 40.5, "cols": cols_r1}
    ]


# ─────────────────────────────────────────────────────────────────────────────
# DEMO / CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random
    
    # Simular salida del motor ML: 15 partidos
    predictions_demo = []
    for i in range(15):
        predictions_demo.append({
            "home": f"Local_{i+1}", 
            "away": f"Visitante_{i+1}",
            "1": 0.4, "X": 0.3, "2": 0.3
        })

    # 1. Probar estrategias
    strats = propose_strategies(predictions_demo)
    for s in strats:
        print(f"Estrategia: {s['name']} - Coste: {s['cost']}€")
        # 2. Exportar primera estrategia como prueba
        if s['id'] == 1:
            export_columns(s['cols'], p15="M-1", filepath="demo_bet.qui")
