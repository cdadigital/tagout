"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import PredictionForm from "@/components/PredictionForm";
import PredictionResult from "@/components/PredictionResult";
import HistoryChart from "@/components/HistoryChart";
import { PredictResponse } from "@/lib/api";

const GMUMap = dynamic(() => import("@/components/GMUMap"), { ssr: false });

export default function PredictPage() {
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [selectedUnit, setSelectedUnit] = useState<string | undefined>();
  const [species, setSpecies] = useState("Elk");

  const handleResult = (r: PredictResponse) => {
    setResult(r);
    setSpecies(r.species);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">2025 Season Forecast</h1>
        <p className="text-gray-400 text-sm mt-1">
          Pick a unit to see predicted success rates for the upcoming season
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Form */}
        <div className="bg-gray-800 rounded-xl p-6">
          <PredictionForm
            onResult={handleResult}
            selectedUnit={selectedUnit}
          />
        </div>

        {/* Center: Map */}
        <div className="bg-gray-800 rounded-xl p-2 h-[500px] lg:h-auto">
          <GMUMap
            species={species}
            onUnitClick={(id) => setSelectedUnit(id)}
          />
        </div>

        {/* Right: Results */}
        <div className="space-y-6">
          {result ? (
            <>
              <div className="bg-gray-800 rounded-xl p-6">
                <PredictionResult result={result} />
              </div>
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
                  Historical Trend — Unit {result.hunt_unit}
                </h3>
                <HistoryChart
                  species={result.species}
                  huntUnit={result.hunt_unit}
                />
              </div>
            </>
          ) : (
            <div className="bg-gray-800 rounded-xl p-8 text-center">
              <div className="text-gray-500 mb-2 text-lg">
                Where are you hunting?
              </div>
              <p className="text-sm text-gray-600">
                Click a unit on the map or pick one from the dropdown
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
