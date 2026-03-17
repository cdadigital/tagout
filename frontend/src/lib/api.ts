const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PredictRequest {
  species: string;
  hunt_unit: string;
  year?: number;
}

export interface PredictResponse {
  species: string;
  hunt_unit: string;
  year: number;
  predicted_success_pct: number;
  historical_avg: number | null;
  confidence_note: string;
  top_factors: Record<string, number>;
}

export interface UnitScore {
  hunt_unit: string;
  species: string;
  predicted_success_pct: number;
  historical_avg: number | null;
}

export interface HarvestStat {
  hunt_unit: string;
  species: string;
  season_year: number;
  success_pct: number | null;
  kills: number | null;
  hunter_count: number | null;
  hunter_days: number | null;
}

export interface Species {
  name: string;
  slug: string;
  description: string;
}

export async function predict(req: PredictRequest): Promise<PredictResponse> {
  const res = await fetch(`${API_BASE}/v1/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function predictMap(
  species: string,
  year: number
): Promise<UnitScore[]> {
  const res = await fetch(
    `${API_BASE}/v1/predict/map?species=${species}&year=${year}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getHarvestStats(
  species: string,
  huntUnit?: string
): Promise<HarvestStat[]> {
  let url = `${API_BASE}/v1/harvest/stats?species=${species}`;
  if (huntUnit) url += `&hunt_unit=${huntUnit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getGmu(): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`${API_BASE}/v1/gmu`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSpecies(): Promise<Species[]> {
  const res = await fetch(`${API_BASE}/v1/species`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
