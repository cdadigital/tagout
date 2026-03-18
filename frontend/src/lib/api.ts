const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PredictRequest {
  species: string;
  hunt_unit: string;
}

export interface PressureInfo {
  level: string;
  avg_hunters: number | null;
  avg_days_per_hunter: number | null;
  total_hunter_days: number | null;
  hunters_trend: string | null;
  panhandle_rank: number | null;
  panhandle_total_units: number;
}

export interface WeatherProfile {
  avg_temp: number;
  avg_high: number;
  avg_low: number;
  first_snow_date: string;
  total_snow_days: number;
  total_precip_days: number;
  max_snow_depth: number;
  snow_total_in: number;
  precip_total_in: number;
}

export interface AntlerQuality {
  antlered_pct: number;
  spike_pct: number | null;
  six_plus_pt_pct: number | null;
  four_pt_pct: number | null;
  five_plus_pt_pct: number | null;
  whitetail_pct: number | null;
  quality_label: string;
}

export interface WeaponBreakdown {
  weapon_type: string;
  weapon_label: string;
  success_pct_3yr: number;
  success_pct_5yr: number;
  avg_hunters: number;
  avg_days_per_hunter: number;
}

export interface PredictResponse {
  species: string;
  hunt_unit: string;
  season: number;
  predicted_success_pct: number;
  historical_3yr_avg: number | null;
  historical_5yr_avg: number | null;
  trend: string;
  pressure: PressureInfo | null;
  confidence_note: string;
  top_factors: Record<string, number>;
  recommendation: string;
  weather_profile: WeatherProfile | null;
  antler_quality: AntlerQuality | null;
  weapon_breakdown: WeaponBreakdown[] | null;
}

export interface UnitScore {
  hunt_unit: string;
  species: string;
  predicted_success_pct: number;
  historical_avg: number | null;
  rank: number;
  trend: string;
}

export interface CompareUnit {
  hunt_unit: string;
  predicted_success_pct: number;
  historical_avg: number | null;
  avg_hunters: number | null;
  avg_days_per_hunter: number | null;
  trend: string;
  pros: string[];
  cons: string[];
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

export async function predict(req: PredictRequest): Promise<PredictResponse> {
  const res = await fetch(`${API_BASE}/v1/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function predictMap(species: string, weaponType?: string): Promise<UnitScore[]> {
  let url = `${API_BASE}/v1/predict/map?species=${species}`;
  if (weaponType && weaponType !== "All Weapons Combined") {
    url += `&weapon_type=${encodeURIComponent(weaponType)}`;
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function compareUnits(
  species: string,
  units: string[]
): Promise<CompareUnit[]> {
  const res = await fetch(
    `${API_BASE}/v1/predict/compare?species=${species}&units=${units.join(",")}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getHarvestStats(
  species: string,
  huntUnit?: string,
  weaponType?: string
): Promise<HarvestStat[]> {
  let url = `${API_BASE}/v1/harvest/stats?species=${species}`;
  if (huntUnit) url += `&hunt_unit=${huntUnit}`;
  if (weaponType && weaponType !== "All Weapons Combined") {
    url += `&weapon_type=${encodeURIComponent(weaponType)}`;
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getGmu(): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`${API_BASE}/v1/gmu`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
