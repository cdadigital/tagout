"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { predictMap, UnitScore } from "@/lib/api";

const GMUMap = dynamic(() => import("@/components/GMUMap"), { ssr: false });

const SPECIES = ["Elk", "Deer"];

export default function MapPage() {
  const [species, setSpecies] = useState("Elk");
  const [rankings, setRankings] = useState<UnitScore[]>([]);

  useEffect(() => {
    predictMap(species).then(setRankings).catch(console.error);
  }, [species]);

  return (
    <div className="h-[calc(100vh-3.5rem)] flex">
      {/* Sidebar rankings */}
      <div className="w-72 bg-gray-800 border-r border-gray-700 overflow-y-auto p-4">
        <div className="mb-4">
          <div className="text-xs text-amber-500 font-medium uppercase tracking-wider mb-2">
            2025 Season Rankings
          </div>
          <div className="flex gap-2">
            {SPECIES.map((s) => (
              <button
                key={s}
                onClick={() => setSpecies(s)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  species === s
                    ? "bg-amber-600 text-white"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          {rankings.map((unit) => (
            <div
              key={unit.hunt_unit}
              className="bg-gray-700/50 rounded-lg p-3 hover:bg-gray-700 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-gray-500 w-5">
                    #{unit.rank}
                  </span>
                  <span className="font-medium text-white">
                    Unit {unit.hunt_unit}
                  </span>
                </div>
                <span className={`font-bold ${
                  unit.predicted_success_pct >= 15 ? "text-green-400" :
                  unit.predicted_success_pct >= 10 ? "text-amber-400" : "text-red-400"
                }`}>
                  {unit.predicted_success_pct}%
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-500">
                  Avg: {unit.historical_avg ?? "—"}%
                </span>
                <span className={`text-xs ${
                  unit.trend === "improving" ? "text-green-500" :
                  unit.trend === "declining" ? "text-red-500" : "text-gray-500"
                }`}>
                  {unit.trend === "improving" ? "↑ improving" :
                   unit.trend === "declining" ? "↓ declining" : "→ stable"}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="mt-6 pt-4 border-t border-gray-700">
          <div className="text-xs text-gray-500 mb-2">Prediction Scale</div>
          <div className="space-y-1 text-xs text-gray-400">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-green-600" /> 20%+ Excellent
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-lime-600" /> 15-20% Good
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-yellow-600" /> 12-15% Fair
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-orange-600" /> 9-12% Below Avg
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-red-600" /> &lt;9% Tough
            </div>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="flex-1">
        <GMUMap species={species} />
      </div>
    </div>
  );
}
