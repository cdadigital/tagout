"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import YoYChart from "@/components/YoYChart";
import { predict, predictMap, PredictResponse, UnitScore, WeaponBreakdown } from "@/lib/api";

const GMUMap = dynamic(() => import("@/components/GMUMap"), { ssr: false });

const UNITS = ["1", "2", "3", "4", "4A", "5", "6", "7", "9"];
const SPECIES = ["Elk", "Deer"];

const WEAPON_OPTIONS = [
  { label: "All", value: "All Weapons Combined" },
  { label: "Rifle", value: "Any Weapon" },
  { label: "Archery", value: "Archery" },
  { label: "Muzz.", value: "Muzzleloader" },
];

function getGrade(pct: number) {
  if (pct >= 25) return { label: "Excellent", color: "text-emerald-400", ring: "ring-emerald-500/30" };
  if (pct >= 15) return { label: "Good", color: "text-amber-400", ring: "ring-amber-500/30" };
  if (pct >= 10) return { label: "Fair", color: "text-yellow-400", ring: "ring-yellow-500/30" };
  return { label: "Tough", color: "text-red-400", ring: "ring-red-500/30" };
}

function getQualityColor(label: string) {
  const l = label.toLowerCase();
  if (l.includes("excellent") || l.includes("above")) return { text: "text-emerald-400", bg: "bg-emerald-500/10" };
  if (l.includes("average") && !l.includes("below")) return { text: "text-yellow-400", bg: "bg-yellow-500/10" };
  if (l.includes("below") || l.includes("poor")) return { text: "text-red-400", bg: "bg-red-500/10" };
  return { text: "text-gray-400", bg: "bg-gray-500/10" };
}

type Tab = "history" | "pressure" | "weather" | "quality" | "compare";

export default function Home() {
  const [species, setSpecies] = useState("Elk");
  const [unit, setUnit] = useState("");
  const [weaponType, setWeaponType] = useState("All Weapons Combined");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [rankings, setRankings] = useState<UnitScore[]>([]);
  const [loading, setLoading] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [tab, setTab] = useState<Tab>("history");

  const isWeaponFiltered = weaponType !== "All Weapons Combined";

  useEffect(() => {
    predictMap(species, weaponType).then(setRankings).catch(console.error);
  }, [species, weaponType]);

  const runPredict = useCallback(async (s: string, u: string) => {
    if (!u) return;
    setLoading(true);
    try {
      const res = await predict({ species: s, hunt_unit: u });
      setResult(res);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (unit) runPredict(species, unit);
  }, [species, unit, runPredict]);

  const handleUnit = (u: string) => {
    setUnit(u);
    setShowMap(false);
  };

  // Find the matching weapon breakdown entry for the selected weapon
  const activeWeapon: WeaponBreakdown | undefined = result?.weapon_breakdown?.find(
    (w) => w.weapon_type === weaponType
  );

  // Hero number: weapon-specific 3yr avg or model prediction
  const heroPct = isWeaponFiltered && activeWeapon
    ? activeWeapon.success_pct_3yr
    : result?.predicted_success_pct ?? 0;

  const grade = result ? getGrade(heroPct) : null;
  const p = result?.pressure;
  const weather = result?.weather_profile;
  const quality = result?.antler_quality;

  // Weapon label for display
  const weaponLabel = WEAPON_OPTIONS.find((w) => w.value === weaponType)?.label ?? "All";

  return (
    <div className="max-w-lg mx-auto px-4 pb-12">
      {/* ── Controls ─────────────────────────────────────── */}
      <div className="sticky top-12 z-40 bg-[#0c0f14] pt-3 pb-2 -mx-4 px-4">
        {/* Species */}
        <div className="flex gap-1.5 p-1 bg-gray-800/50 rounded-xl mb-2">
          {SPECIES.map((s) => (
            <button
              key={s}
              onClick={() => setSpecies(s)}
              className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                species === s
                  ? "bg-amber-600 text-white shadow-lg shadow-amber-600/20"
                  : "text-gray-500 active:bg-gray-700/50"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        {/* Weapon toggle */}
        <div className="flex gap-1 p-0.5 bg-gray-800/40 rounded-lg mb-2">
          {WEAPON_OPTIONS.map((w) => (
            <button
              key={w.value}
              onClick={() => setWeaponType(w.value)}
              className={`flex-1 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 ${
                weaponType === w.value
                  ? "bg-gray-700/80 text-amber-400"
                  : "text-gray-600 active:bg-gray-700/30"
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
        {/* Unit */}
        <div className="relative">
          <select
            value={unit}
            onChange={(e) => handleUnit(e.target.value)}
            className="w-full px-4 py-3 bg-gray-800/50 text-white rounded-xl border border-gray-700/40 focus:border-amber-500/50 focus:outline-none text-base appearance-none cursor-pointer"
          >
            <option value="">Select a hunt unit...</option>
            {UNITS.map((u) => {
              const r = rankings.find((rk) => rk.hunt_unit === u);
              return (
                <option key={u} value={u}>
                  Unit {u}{r ? ` — ${r.predicted_success_pct}%` : ""}
                </option>
              );
            })}
          </select>
          <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-600">
            <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M5 7L1 3h8L5 7z" /></svg>
          </div>
        </div>
      </div>

      {/* Map toggle */}
      {!result && (
        <button
          onClick={() => setShowMap(!showMap)}
          className="w-full py-2 text-xs text-gray-600 flex items-center justify-center gap-1 mb-2"
        >
          {showMap ? "Hide map" : "Or tap the map"}
          <svg width="8" height="8" viewBox="0 0 10 10" fill="currentColor"
            className={`transition-transform duration-200 ${showMap ? "rotate-180" : ""}`}
          ><path d="M5 7L1 3h8L5 7z" /></svg>
        </button>
      )}
      {showMap && (
        <div className="mb-4 rounded-2xl overflow-hidden h-[260px] border border-gray-700/40">
          <GMUMap species={species} onUnitClick={handleUnit} />
        </div>
      )}

      {/* ── Loading ──────────────────────────────────────── */}
      {loading && (
        <div className="text-center py-20">
          <div className="inline-block w-7 h-7 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
        </div>
      )}

      {/* ── Empty: Show Rankings ─────────────────────────── */}
      {!unit && !loading && (
        <div className="mt-2">
          <div className="text-[11px] text-gray-600 uppercase tracking-widest mb-3 px-1">
            {species} — {isWeaponFiltered
              ? `${weaponLabel} 3yr Avg`
              : "2025 Season Rankings"}
          </div>
          <div className="space-y-1">
            {rankings.map((r) => (
              <button
                key={r.hunt_unit}
                onClick={() => handleUnit(r.hunt_unit)}
                className="w-full card flex items-center justify-between px-4 py-3.5 active:scale-[0.98] transition-transform"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-gray-600 w-5 text-right">
                    {r.rank}.
                  </span>
                  <span className="font-semibold text-white">Unit {r.hunt_unit}</span>
                  {r.trend !== "stable" && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      r.trend === "improving"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-red-500/10 text-red-400"
                    }`}>
                      {r.trend === "improving" ? "up" : "down"}
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-1">
                  <span className={`text-lg font-bold tabular-nums ${
                    r.predicted_success_pct >= 15 ? "text-emerald-400" :
                    r.predicted_success_pct >= 10 ? "text-amber-400" : "text-red-400"
                  }`}>
                    {r.predicted_success_pct}
                  </span>
                  <span className="text-xs text-gray-600">%</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Results ──────────────────────────────────────── */}
      {result && !loading && (
        <div className="mt-1 space-y-3">

          {/* Hero: Score + Context + Recommendation */}
          <div className={`card p-5 ring-1 ${grade?.ring}`}>
            {/* Score row */}
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[10px] text-gray-600 uppercase tracking-widest">
                  Unit {result.hunt_unit} &bull; {result.species}
                </div>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-5xl font-bold text-white score-glow tracking-tight">
                    {heroPct}
                  </span>
                  <span className="text-xl text-gray-500">%</span>
                </div>
                {isWeaponFiltered && activeWeapon ? (
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    3yr Avg ({activeWeapon.weapon_label})
                  </div>
                ) : (
                  <div className="text-[10px] text-gray-600 mt-0.5">2025 forecast</div>
                )}
              </div>
              <div className="text-right">
                <div className={`text-sm font-semibold ${grade?.color}`}>{grade?.label}</div>
                {isWeaponFiltered && (
                  <div className="text-[10px] text-gray-500 mt-1">
                    All-weapon forecast:{" "}
                    <span className="text-white font-semibold">{result.predicted_success_pct}%</span>
                  </div>
                )}
              </div>
            </div>

            {/* Comparison strip */}
            <div className="flex gap-4 py-3 border-t border-b border-gray-700/30 mb-4">
              {isWeaponFiltered && activeWeapon ? (
                <>
                  <div className="flex-1">
                    <span className="text-white font-semibold tabular-nums">{activeWeapon.success_pct_3yr}%</span>
                    <span className="text-[10px] text-gray-500 ml-1.5">3yr avg</span>
                  </div>
                  <div className="flex-1">
                    <span className="text-white font-semibold tabular-nums">{activeWeapon.success_pct_5yr}%</span>
                    <span className="text-[10px] text-gray-500 ml-1.5">5yr avg</span>
                  </div>
                  <div>
                    <span className="text-white font-semibold tabular-nums">{activeWeapon.avg_days_per_hunter}</span>
                    <span className="text-[10px] text-gray-500 ml-1.5">days/hunter</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex-1">
                    <span className="text-white font-semibold tabular-nums">{result.historical_3yr_avg ?? "—"}%</span>
                    <span className="text-[10px] text-gray-500 ml-1.5">3yr avg</span>
                  </div>
                  <div className="flex-1">
                    <span className="text-white font-semibold tabular-nums">{result.historical_5yr_avg ?? "—"}%</span>
                    <span className="text-[10px] text-gray-500 ml-1.5">5yr avg</span>
                  </div>
                  <div>
                    <span className={`font-semibold ${
                      result.trend === "improving" ? "text-emerald-400" :
                      result.trend === "declining" ? "text-red-400" : "text-gray-400"
                    }`}>
                      {result.trend === "improving" ? "↑" : result.trend === "declining" ? "↓" : "→"}
                    </span>
                    <span className="text-[10px] text-gray-500 ml-1.5 capitalize">{result.trend}</span>
                  </div>
                </>
              )}
            </div>

            {/* Weapon breakdown mini-row (when showing all weapons) */}
            {!isWeaponFiltered && result.weapon_breakdown && result.weapon_breakdown.length > 0 && (
              <div className="flex gap-3 pb-3 mb-3 border-b border-gray-700/30">
                {result.weapon_breakdown.map((w) => (
                  <button
                    key={w.weapon_type}
                    onClick={() => setWeaponType(w.weapon_type)}
                    className="flex-1 text-center group"
                  >
                    <div className="text-sm font-bold text-white tabular-nums group-active:text-amber-400">
                      {w.success_pct_3yr}%
                    </div>
                    <div className="text-[9px] text-gray-600 uppercase">
                      {w.weapon_label}
                      {w.avg_hunters < 20 && (
                        <span className="block text-yellow-600">Small sample</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Recommendation */}
            <p className="text-[13px] text-gray-300 leading-relaxed">
              {result.recommendation}
            </p>
          </div>

          {/* ── Tab Bar (scrollable) ─────────────────────── */}
          <div className="overflow-x-auto whitespace-nowrap -mx-4 px-4">
            <div className="inline-flex gap-1 p-1 bg-gray-800/40 rounded-xl min-w-full">
              {([
                { key: "history" as Tab, label: "History" },
                { key: "pressure" as Tab, label: "Pressure" },
                { key: "weather" as Tab, label: "Weather" },
                { key: "quality" as Tab, label: "Quality" },
                { key: "compare" as Tab, label: "All Units" },
              ]).map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`flex-shrink-0 flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all duration-150 ${
                    tab === t.key
                      ? "bg-gray-700/80 text-white"
                      : "text-gray-500 active:bg-gray-700/30"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* ── Tab: History ───────────────────────────── */}
          {tab === "history" && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-[11px] text-gray-500 uppercase tracking-widest">
                  Year-over-Year Success
                </h3>
                <span className="text-[10px] text-gray-600">
                  Unit {result.hunt_unit}
                  {isWeaponFiltered && ` · ${weaponLabel}`}
                </span>
              </div>
              <YoYChart
                species={result.species}
                huntUnit={result.hunt_unit}
                predictedPct={result.predicted_success_pct}
                predictedYear={result.season}
                weaponType={weaponType}
              />
            </div>
          )}

          {/* ── Tab: Pressure ──────────────────────────── */}
          {tab === "pressure" && p && (
            <div className="card p-5">
              {/* Level + rank */}
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2.5">
                  <div className={`w-2.5 h-2.5 rounded-full ${
                    p.level === "low" ? "bg-emerald-400" :
                    p.level === "high" ? "bg-red-400" : "bg-yellow-400"
                  }`} />
                  <span className={`text-xl font-bold capitalize ${
                    p.level === "low" ? "text-emerald-400" :
                    p.level === "high" ? "text-red-400" : "text-yellow-400"
                  }`}>
                    {p.level} Pressure
                  </span>
                </div>
                {p.panhandle_rank && (
                  <span className="text-xs text-gray-500 bg-gray-700/50 px-2 py-1 rounded-lg">
                    #{p.panhandle_rank} of {p.panhandle_total_units}
                  </span>
                )}
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-white tabular-nums">
                    {p.avg_hunters ? (p.avg_hunters / 1000).toFixed(1) : "—"}
                  </div>
                  <div className="text-[10px] text-gray-500 uppercase mt-0.5">
                    K Hunters
                    {p.hunters_trend === "increasing" && <span className="text-red-400"> ↑</span>}
                    {p.hunters_trend === "decreasing" && <span className="text-emerald-400"> ↓</span>}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white tabular-nums">
                    {p.avg_days_per_hunter ?? "—"}
                  </div>
                  <div className="text-[10px] text-gray-500 uppercase mt-0.5">Days Each</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white tabular-nums">
                    {p.total_hunter_days ? `${(p.total_hunter_days / 1000).toFixed(0)}k` : "—"}
                  </div>
                  <div className="text-[10px] text-gray-500 uppercase mt-0.5">Total Days</div>
                </div>
              </div>

              {/* Context */}
              <div className="text-xs text-gray-500 leading-relaxed border-t border-gray-700/30 pt-3">
                {p.level === "high"
                  ? "This unit sees heavy traffic. Hunt midweek or push into backcountry for less competition."
                  : p.level === "low"
                  ? "One of the quieter units in the Panhandle. Fewer hunters means less spooked game."
                  : "Moderate competition. You won't be alone, but it's not shoulder-to-shoulder either."}
                {" "}Based on 5-year average hunter counts from IDFG.
              </div>
            </div>
          )}

          {/* ── Tab: Weather ────────────────────────────── */}
          {tab === "weather" && (
            <div className="card p-5">
              {weather ? (
                <>
                  <div className="flex items-center justify-between mb-5">
                    <h3 className="text-[11px] text-gray-500 uppercase tracking-widest">
                      Season Weather Normals
                    </h3>
                    <span className="text-[10px] text-gray-600">
                      Unit {result.hunt_unit}
                    </span>
                  </div>

                  {/* First snow callout */}
                  <div className="text-center mb-5 py-3 bg-blue-500/5 rounded-xl border border-blue-500/10">
                    <div className="text-[10px] text-blue-400/60 uppercase tracking-widest mb-1">
                      First Snow
                    </div>
                    <div className="text-2xl font-bold text-blue-300">
                      {weather.first_snow_date}
                    </div>
                  </div>

                  {/* Weather grid */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-white tabular-nums">
                        {weather.avg_high}° / {weather.avg_low}°
                      </div>
                      <div className="text-[10px] text-gray-500 uppercase mt-0.5">Avg High / Low</div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-white tabular-nums">
                        {weather.total_snow_days}
                      </div>
                      <div className="text-[10px] text-gray-500 uppercase mt-0.5">Snow Days</div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-white tabular-nums">
                        {weather.max_snow_depth}&quot;
                      </div>
                      <div className="text-[10px] text-gray-500 uppercase mt-0.5">Max Depth</div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-white tabular-nums">
                        {weather.snow_total_in}&quot;
                      </div>
                      <div className="text-[10px] text-gray-500 uppercase mt-0.5">Total Snow</div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-white tabular-nums">
                        {weather.total_precip_days}
                      </div>
                      <div className="text-[10px] text-gray-500 uppercase mt-0.5">Precip Days</div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-white tabular-nums">
                        {weather.precip_total_in}&quot;
                      </div>
                      <div className="text-[10px] text-gray-500 uppercase mt-0.5">Total Precip</div>
                    </div>
                  </div>

                  {/* Context */}
                  <div className="text-xs text-gray-500 leading-relaxed border-t border-gray-700/30 pt-3">
                    Historical weather averages during hunting season. Early snow pushes
                    elk to lower elevations and can dramatically improve success rates.
                  </div>
                </>
              ) : (
                <div className="text-gray-600 text-xs py-8 text-center">
                  No weather data available for this unit.
                </div>
              )}
            </div>
          )}

          {/* ── Tab: Quality (Antler) ──────────────────── */}
          {tab === "quality" && (
            <div className="card p-5">
              {quality ? (
                <>
                  <div className="flex items-center justify-between mb-5">
                    <h3 className="text-[11px] text-gray-500 uppercase tracking-widest">
                      Antler Quality
                    </h3>
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${getQualityColor(quality.quality_label).text} ${getQualityColor(quality.quality_label).bg}`}>
                      {quality.quality_label}
                    </span>
                  </div>

                  {/* Antlered ratio */}
                  <div className="mb-5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-500">Antlered</span>
                      <span className="text-xs text-gray-500">Antlerless</span>
                    </div>
                    <div className="h-3 bg-gray-700/50 rounded-full overflow-hidden flex">
                      <div
                        className="bg-amber-500/80 rounded-l-full transition-all duration-500"
                        style={{ width: `${quality.antlered_pct}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs font-semibold text-amber-400 tabular-nums">
                        {quality.antlered_pct}%
                      </span>
                      <span className="text-xs font-semibold text-gray-500 tabular-nums">
                        {(100 - quality.antlered_pct).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Species-specific quality metrics */}
                  {species === "Elk" ? (
                    <div className="grid grid-cols-2 gap-3 mb-4">
                      {quality.spike_pct !== null && (
                        <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                          <div className="text-2xl font-bold text-white tabular-nums">
                            {quality.spike_pct}%
                          </div>
                          <div className="text-[10px] text-gray-500 uppercase mt-0.5">Spikes</div>
                        </div>
                      )}
                      {quality.six_plus_pt_pct !== null && (
                        <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                          <div className="text-2xl font-bold text-emerald-400 tabular-nums">
                            {quality.six_plus_pt_pct}%
                          </div>
                          <div className="text-[10px] text-gray-500 uppercase mt-0.5">6+ Point</div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-3 mb-4">
                      {quality.four_pt_pct !== null && (
                        <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                          <div className="text-2xl font-bold text-white tabular-nums">
                            {quality.four_pt_pct}%
                          </div>
                          <div className="text-[10px] text-gray-500 uppercase mt-0.5">4-Point</div>
                        </div>
                      )}
                      {quality.five_plus_pt_pct !== null && (
                        <div className="bg-gray-800/30 rounded-xl p-3 text-center">
                          <div className="text-2xl font-bold text-emerald-400 tabular-nums">
                            {quality.five_plus_pt_pct}%
                          </div>
                          <div className="text-[10px] text-gray-500 uppercase mt-0.5">5+ Point</div>
                        </div>
                      )}
                      {quality.whitetail_pct !== null && (
                        <div className="bg-gray-800/30 rounded-xl p-3 text-center col-span-2">
                          <div className="text-2xl font-bold text-white tabular-nums">
                            {quality.whitetail_pct}%
                          </div>
                          <div className="text-[10px] text-gray-500 uppercase mt-0.5">Whitetail</div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Context */}
                  <div className="text-xs text-gray-500 leading-relaxed border-t border-gray-700/30 pt-3">
                    {species === "Elk"
                      ? "Spike percentage indicates younger bulls; higher 6+ point rates suggest a mature herd with better trophy potential."
                      : "Point class breakdown from IDFG harvest surveys. Higher 5+ point rates indicate stronger age structure and trophy opportunity."}
                  </div>
                </>
              ) : (
                <div className="text-gray-600 text-xs py-8 text-center">
                  No antler quality data available for this unit.
                </div>
              )}
            </div>
          )}

          {/* ── Tab: All Units ─────────────────────────── */}
          {tab === "compare" && (
            <div className="card p-4">
              <div className="text-[11px] text-gray-600 uppercase tracking-widest mb-3 px-1">
                {isWeaponFiltered ? `${weaponLabel} 3yr Avg` : "2025 Season Rankings"}
              </div>
              <div className="space-y-1">
                {rankings.map((r) => {
                  const isCurrent = r.hunt_unit === unit;
                  return (
                    <button
                      key={r.hunt_unit}
                      onClick={() => handleUnit(r.hunt_unit)}
                      className={`w-full flex items-center px-3 py-3 rounded-xl text-sm transition-all duration-150 ${
                        isCurrent
                          ? "bg-amber-500/10 ring-1 ring-amber-500/30"
                          : "active:bg-gray-700/40"
                      }`}
                    >
                      <span className="text-[11px] font-bold text-gray-600 w-6 text-right mr-3 tabular-nums">
                        {r.rank}
                      </span>
                      <span className={`font-semibold flex-1 text-left ${isCurrent ? "text-amber-400" : "text-white"}`}>
                        Unit {r.hunt_unit}
                      </span>
                      {r.trend !== "stable" && (
                        <span className={`text-[10px] mr-3 ${
                          r.trend === "improving" ? "text-emerald-500" : "text-red-500"
                        }`}>
                          {r.trend === "improving" ? "↑" : "↓"}
                        </span>
                      )}
                      <div className="flex items-baseline gap-0.5 w-14 justify-end">
                        <span className={`text-base font-bold tabular-nums ${
                          r.predicted_success_pct >= 15 ? "text-emerald-400" :
                          r.predicted_success_pct >= 10 ? "text-amber-400" : "text-red-400"
                        }`}>
                          {r.predicted_success_pct}
                        </span>
                        <span className="text-[10px] text-gray-600">%</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Map (inline, compact when results showing) */}
          {!showMap && result && (
            <button
              onClick={() => setShowMap(true)}
              className="w-full py-2 text-xs text-gray-600 flex items-center justify-center gap-1"
            >
              Show map
              <svg width="8" height="8" viewBox="0 0 10 10" fill="currentColor"><path d="M5 7L1 3h8L5 7z" /></svg>
            </button>
          )}
          {showMap && result && (
            <div className="rounded-2xl overflow-hidden h-[240px] border border-gray-700/40">
              <GMUMap species={species} onUnitClick={handleUnit} />
            </div>
          )}

          {/* Disclaimer */}
          <p className="text-[10px] text-gray-700 text-center leading-relaxed pt-2">
            Based on 22 years of IDFG data + historical weather. Not a guarantee.
          </p>
        </div>
      )}
    </div>
  );
}
