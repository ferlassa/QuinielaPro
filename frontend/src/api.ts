const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface MatchInput {
  home_elo: number;
  away_elo: number;
  home_xg: number;
  away_xg: number;
}

export interface PredictResult {
  partido: number;
  prob_1: number;
  prob_X: number;
  prob_2: number;
  signo_mas_probable: string;
  pleno15_resultado: string;
  pleno15_prob: number;
}

export interface OptimizeResult {
  reduccion: string;
  garantia_aciertos: number;
  columnas_generadas: number;
  columnas_filtradas_megaquin: number;
  columnas_finales: number;
  columnas: string[];
  archivo_qui: string;
}

export interface KellyResult {
  edge: number;
  f_star_full: number;
  f_star_frac: number;
  apuesta_euros: number;
  riesgo: string;
  esperanza_matematica: number;
}

export interface RoiResult {
  periodo: number;
  jornadas: number;
  invertido: number;
  recuperado: number;
  beneficio: number;
  "roi_%": number;
  aciertos_medios: number;
}

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export async function predictJornada(matches: MatchInput[]): Promise<PredictResult[]> {
  const data = await fetchJSON<{ jornada: PredictResult[] }>("/predict", {
    method: "POST",
    body: JSON.stringify({ matches }),
  });
  return data.jornada;
}

export async function optimizeColumns(
  matches: MatchInput[],
  reduction: string = "R1"
): Promise<OptimizeResult> {
  return fetchJSON<OptimizeResult>("/optimize", {
    method: "POST",
    body: JSON.stringify({ jornada: { matches }, reduction }),
  });
}

export async function getKelly(
  prob_win: number,
  prize_euros: number,
  bankroll: number,
  kelly_fraction = 0.25
): Promise<KellyResult> {
  return fetchJSON<KellyResult>("/kelly", {
    method: "POST",
    body: JSON.stringify({ prob_win, prize_euros, bankroll, kelly_fraction }),
  });
}

export async function getRoi(periodo: number = 10): Promise<RoiResult> {
  return fetchJSON<RoiResult>(`/roi?periodo=${periodo}`);
}

export async function getJornadas(limit = 10) {
  return fetchJSON<Array<{ id: number; numero: number; fecha: string }>>(`/jornadas?limit=${limit}`);
}

/** Genera 14 partidos demo para cuando no hay datos reales */
export function demoMatches(): MatchInput[] {
  return Array.from({ length: 14 }, () => ({
    home_elo: 1500 + Math.random() * 400 - 200,
    away_elo: 1500 + Math.random() * 400 - 200,
    home_xg: 0.8 + Math.random() * 2,
    away_xg: 0.6 + Math.random() * 1.8,
  }));
}
