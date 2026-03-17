"use client";

import { PredictResponse } from "@/lib/api";

function getGrade(pct: number): { label: string; color: string } {
  if (pct >= 25) return { label: "Excellent", color: "text-green-400" };
  if (pct >= 15) return { label: "Good", color: "text-amber-400" };
  if (pct >= 10) return { label: "Fair", color: "text-yellow-400" };
  return { label: "Low", color: "text-red-400" };
}

const FACTOR_LABELS: Record<string, string> = {
  success_3yr_avg: "Historical success rate",
  snow_days: "Snow days in season",
  precip_total_in: "Total precipitation",
  temp_mean: "Average temperature",
  wind_avg_max: "Wind conditions",
  pressure_std: "Weather variability",
  daylight_avg_hrs: "Daylight hours",
  year_offset: "Year trend",
  days_per_hunter: "Avg days per hunter",
};

export default function PredictionResult({
  result,
}: {
  result: PredictResponse;
}) {
  const grade = getGrade(result.predicted_success_pct);

  return (
    <div className="space-y-4">
      {/* Main score */}
      <div className="text-center py-6">
        <div className="text-6xl font-bold text-white">
          {result.predicted_success_pct}%
        </div>
        <div className={`text-lg font-medium mt-1 ${grade.color}`}>
          {grade.label}
        </div>
        <div className="text-gray-400 text-sm mt-2">
          Predicted success rate for {result.species} in Unit{" "}
          {result.hunt_unit} ({result.year})
        </div>
      </div>

      {/* Historical comparison */}
      {result.historical_avg !== null && (
        <div className="bg-gray-700/50 rounded-lg p-4">
          <div className="flex justify-between items-center">
            <span className="text-gray-300 text-sm">3-Year Historical Avg</span>
            <span className="text-white font-medium">
              {result.historical_avg}%
            </span>
          </div>
          <div className="flex justify-between items-center mt-2">
            <span className="text-gray-300 text-sm">Model Prediction</span>
            <span className="text-amber-400 font-medium">
              {result.predicted_success_pct}%
            </span>
          </div>
          {result.predicted_success_pct !== result.historical_avg && (
            <div className="mt-2 text-xs text-gray-400">
              {result.predicted_success_pct > result.historical_avg
                ? `+${(result.predicted_success_pct - result.historical_avg).toFixed(1)}pp above average — weather conditions favor success`
                : `${(result.predicted_success_pct - result.historical_avg).toFixed(1)}pp below average — conditions may be less favorable`}
            </div>
          )}
        </div>
      )}

      {/* Top factors */}
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-2">
          Key Factors
        </h3>
        <div className="space-y-2">
          {Object.entries(result.top_factors)
            .slice(0, 5)
            .map(([key, value]) => (
              <div key={key} className="flex items-center gap-2">
                <div className="flex-1">
                  <div className="text-xs text-gray-400">
                    {FACTOR_LABELS[key] || key.replace(/_/g, " ")}
                  </div>
                  <div className="h-1.5 bg-gray-700 rounded-full mt-1">
                    <div
                      className="h-1.5 bg-amber-500 rounded-full"
                      style={{ width: `${Math.min(value * 500, 100)}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs text-gray-500 w-12 text-right">
                  {(value * 100).toFixed(1)}%
                </span>
              </div>
            ))}
        </div>
      </div>

      <p className="text-xs text-gray-500 italic">{result.confidence_note}</p>
    </div>
  );
}
