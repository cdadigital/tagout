"use client";

import { PredictResponse } from "@/lib/api";

function getGrade(pct: number): { label: string; color: string; bg: string } {
  if (pct >= 25) return { label: "Excellent", color: "text-green-400", bg: "bg-green-500/20" };
  if (pct >= 15) return { label: "Good", color: "text-amber-400", bg: "bg-amber-500/20" };
  if (pct >= 10) return { label: "Fair", color: "text-yellow-400", bg: "bg-yellow-500/20" };
  return { label: "Tough", color: "text-red-400", bg: "bg-red-500/20" };
}

const TREND_ICONS: Record<string, string> = {
  improving: "Trending Up",
  declining: "Trending Down",
  stable: "Stable",
};

export default function PredictionResult({ result }: { result: PredictResponse }) {
  const grade = getGrade(result.predicted_success_pct);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="text-xs text-amber-500 font-medium uppercase tracking-wider">
        {result.season} Season — Unit {result.hunt_unit} — {result.species}
      </div>

      {/* Main score */}
      <div className={`text-center py-5 rounded-lg ${grade.bg}`}>
        <div className="text-5xl font-bold text-white">
          {result.predicted_success_pct}%
        </div>
        <div className={`text-sm font-medium mt-1 ${grade.color}`}>
          {grade.label} Odds
        </div>
      </div>

      {/* Key stats row */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="text-lg font-bold text-white">
            {result.historical_3yr_avg ?? "—"}%
          </div>
          <div className="text-xs text-gray-400">3-yr Avg</div>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="text-lg font-bold text-white">
            {result.historical_5yr_avg ?? "—"}%
          </div>
          <div className="text-xs text-gray-400">5-yr Avg</div>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className={`text-lg font-bold ${
            result.trend === "improving" ? "text-green-400" :
            result.trend === "declining" ? "text-red-400" : "text-gray-300"
          }`}>
            {TREND_ICONS[result.trend] || result.trend}
          </div>
          <div className="text-xs text-gray-400">Trend</div>
        </div>
      </div>

      {/* Hunter pressure */}
      {result.hunter_pressure && (
        <div className="flex items-center justify-between bg-gray-700/50 rounded-lg px-4 py-2">
          <span className="text-sm text-gray-300">Hunter Pressure</span>
          <span className={`text-sm font-medium capitalize ${
            result.hunter_pressure === "low" ? "text-green-400" :
            result.hunter_pressure === "high" ? "text-red-400" : "text-yellow-400"
          }`}>
            {result.hunter_pressure}
          </span>
        </div>
      )}

      {/* Recommendation */}
      <div className="bg-gray-700/30 border border-gray-600 rounded-lg p-4">
        <p className="text-sm text-gray-200 leading-relaxed">
          {result.recommendation}
        </p>
      </div>

      {/* Top factors */}
      <div>
        <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
          What Drives This Prediction
        </h3>
        <div className="space-y-1.5">
          {Object.entries(result.top_factors)
            .slice(0, 5)
            .map(([key, value]) => (
              <div key={key} className="flex items-center gap-2">
                <div className="flex-1">
                  <div className="text-xs text-gray-300">{key}</div>
                  <div className="h-1 bg-gray-700 rounded-full mt-0.5">
                    <div
                      className="h-1 bg-amber-500 rounded-full"
                      style={{ width: `${Math.min(value * 500, 100)}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs text-gray-500 w-10 text-right">
                  {(value * 100).toFixed(0)}%
                </span>
              </div>
            ))}
        </div>
      </div>

      <p className="text-xs text-gray-600 italic">{result.confidence_note}</p>
    </div>
  );
}
