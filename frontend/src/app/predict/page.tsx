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

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Predict Hunt Success</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Form */}
        <div className="bg-gray-800 rounded-xl p-6">
          <PredictionForm
            onResult={setResult}
            selectedUnit={selectedUnit}
          />
        </div>

        {/* Center: Map */}
        <div className="bg-gray-800 rounded-xl p-2 h-[500px] lg:h-auto">
          <GMUMap
            species={result?.species || "Elk"}
            year={result?.year || 2024}
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
                <h3 className="text-sm font-medium text-gray-300 mb-3">
                  Historical Trend — Unit {result.hunt_unit}
                </h3>
                <HistoryChart
                  species={result.species}
                  huntUnit={result.hunt_unit}
                />
              </div>
            </>
          ) : (
            <div className="bg-gray-800 rounded-xl p-6 text-center text-gray-500">
              <p className="text-lg">Select a unit and run a prediction</p>
              <p className="text-sm mt-2">
                Click a unit on the map or use the form
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
