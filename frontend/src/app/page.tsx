"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import YoYChart from "@/components/YoYChart";
import { predict, predictMap, PredictResponse, UnitScore } from "@/lib/api";

const GMUMap = dynamic(() => import("@/components/GMUMap"), { ssr: false });

const UNITS = ["1", "2", "3", "4", "4A", "5", "6", "7", "9"];
const SPECIES = ["Elk", "Deer"];

function getGrade(pct: number) {
  if (pct >= 25) return { label: "Excellent", color: "text-emerald-400", glow: "shadow-emerald-500/20" };
  if (pct >= 15) return { label: "Good", color: "text-amber-400", glow: "shadow-amber-500/20" };
  if (pct >= 10) return { label: "Fair", color: "text-yellow-400", glow: "shadow-yellow-500/20" };
  return { label: "Tough", color: "text-red-400", glow: "shadow-red-500/20" };
}

export default function Home() {
  const [species, setSpecies] = useState("Elk");
  const [unit, setUnit] = useState("");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [rankings, setRankings] = useState<UnitScore[]>([]);
  const [loading, setLoading] = useState(false);
  const [showMap, setShowMap] = useState(false);

  useEffect(() => {
    predictMap(species).then(setRankings).catch(console.error);
  }, [species]);

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

  const grade = result ? getGrade(result.predicted_success_pct) : null;

  return (
    <div className="max-w-lg mx-auto px-4 pb-12">
      {/* Species Toggle */}
      <div className="pt-5 pb-3">
        <div className="flex gap-2 p-1 bg-gray-800/60 rounded-xl">
          {SPECIES.map((s) => (
            <button
              key={s}
              onClick={() => setSpecies(s)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
                species === s
                  ? "bg-amber-600 text-white shadow-lg shadow-amber-600/25"
                  : "text-gray-400 active:bg-gray-700/50"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Unit Picker */}
      <div className="pb-3">
        <div className="relative">
          <select
            value={unit}
            onChange={(e) => handleUnit(e.target.value)}
            className="w-full px-4 py-3.5 bg-gray-800/60 text-white rounded-xl border border-gray-700/50 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 focus:outline-none text-base appearance-none cursor-pointer transition-colors"
          >
            <option value="">Select a hunt unit...</option>
            {UNITS.map((u) => {
              const r = rankings.find((rk) => rk.hunt_unit === u);
              return (
                <option key={u} value={u}>
                  Unit {u}{r ? ` — ${r.predicted_success_pct}% forecast` : ""}
                </option>
              );
            })}
          </select>
          <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
              <path d="M6 8.5L1 3.5h10L6 8.5z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Map Toggle */}
      <div className="pb-5">
        <button
          onClick={() => setShowMap(!showMap)}
          className="w-full py-2.5 text-sm text-gray-500 rounded-xl active:bg-gray-800/40 transition-colors flex items-center justify-center gap-1.5"
        >
          {showMap ? "Hide map" : "Or pick from map"}
          <svg
            width="10" height="10" viewBox="0 0 10 10" fill="currentColor"
            className={`transition-transform duration-200 ${showMap ? "rotate-180" : ""}`}
          >
            <path d="M5 7L1 3h8L5 7z" />
          </svg>
        </button>
        {showMap && (
          <div className="mt-2 rounded-2xl overflow-hidden h-[280px] border border-gray-700/50 shadow-xl shadow-black/30">
            <GMUMap species={species} onUnitClick={handleUnit} />
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-16">
          <div className="inline-block w-8 h-8 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
        </div>
      )}

      {/* Empty state */}
      {!unit && !loading && (
        <div className="text-center py-16 px-4">
          <div className="text-gray-700 text-sm">
            Pick a unit to see your 2025 season forecast
          </div>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-3">
          {/* Hero prediction */}
          <div className={`card text-center py-8 px-6 shadow-xl ${grade?.glow}`}>
            <div className="text-[11px] text-gray-500 tracking-widest uppercase mb-3">
              {result.species} &bull; Unit {result.hunt_unit} &bull; {result.season} Season
            </div>
            <div className="text-6xl font-bold text-white score-glow tracking-tight">
              {result.predicted_success_pct}<span className="text-3xl text-gray-400">%</span>
            </div>
            <div className={`text-sm font-semibold mt-2 ${grade?.color}`}>
              {grade?.label}
            </div>
          </div>

          {/* Stats strip */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { value: `${result.historical_3yr_avg ?? "—"}%`, label: "3-yr Avg" },
              { value: `${result.historical_5yr_avg ?? "—"}%`, label: "5-yr Avg" },
              {
                value: result.trend === "improving" ? "↑" : result.trend === "declining" ? "↓" : "→",
                label: result.trend.charAt(0).toUpperCase() + result.trend.slice(1),
                color: result.trend === "improving" ? "text-emerald-400" : result.trend === "declining" ? "text-red-400" : "text-gray-400",
              },
            ].map((stat, i) => (
              <div key={i} className="card py-3 text-center">
                <div className={`text-xl font-bold ${stat.color || "text-white"}`}>
                  {stat.value}
                </div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>

          {/* YoY Chart */}
          <div className="card p-5">
            <h3 className="text-[11px] text-gray-500 uppercase tracking-widest mb-4">
              Year-over-Year
            </h3>
            <YoYChart
              species={result.species}
              huntUnit={result.hunt_unit}
              predictedPct={result.predicted_success_pct}
              predictedYear={result.season}
            />
          </div>

          {/* Recommendation */}
          <div className="card p-5">
            <p className="text-[13px] text-gray-300 leading-relaxed">
              {result.recommendation}
            </p>
            {result.hunter_pressure && (
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-700/40">
                <span className="text-xs text-gray-500">Hunter Pressure</span>
                <span className={`text-xs font-semibold capitalize ${
                  result.hunter_pressure === "low" ? "text-emerald-400" :
                  result.hunter_pressure === "high" ? "text-red-400" : "text-yellow-400"
                }`}>
                  {result.hunter_pressure}
                </span>
              </div>
            )}
          </div>

          {/* Unit Rankings */}
          <div className="card p-5">
            <h3 className="text-[11px] text-gray-500 uppercase tracking-widest mb-3">
              {species} Unit Rankings
            </h3>
            <div className="space-y-1">
              {rankings.map((r) => (
                <button
                  key={r.hunt_unit}
                  onClick={() => handleUnit(r.hunt_unit)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm transition-all duration-150 ${
                    r.hunt_unit === unit
                      ? "bg-amber-500/10 border border-amber-500/30"
                      : "active:bg-gray-700/50 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-[11px] font-bold text-gray-600 w-4">
                      {r.rank}
                    </span>
                    <span className="font-medium text-white">
                      Unit {r.hunt_unit}
                    </span>
                    <span className={`text-xs ${
                      r.trend === "improving" ? "text-emerald-500" :
                      r.trend === "declining" ? "text-red-500" : "text-gray-600"
                    }`}>
                      {r.trend === "improving" ? "↑" : r.trend === "declining" ? "↓" : ""}
                    </span>
                  </div>
                  <span className={`font-bold tabular-nums ${
                    r.predicted_success_pct >= 15 ? "text-emerald-400" :
                    r.predicted_success_pct >= 10 ? "text-amber-400" : "text-red-400"
                  }`}>
                    {r.predicted_success_pct}%
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Disclaimer */}
          <p className="text-[10px] text-gray-700 text-center px-4 py-2 leading-relaxed">
            {result.confidence_note}
          </p>
        </div>
      )}
    </div>
  );
}
