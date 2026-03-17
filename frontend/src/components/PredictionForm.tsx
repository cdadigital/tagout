"use client";

import { useState } from "react";
import { predict, PredictResponse } from "@/lib/api";

const UNITS = ["1", "2", "3", "4", "4A", "5", "6", "7", "9"];
const SPECIES = ["Elk", "Deer"];
const YEARS = Array.from({ length: 22 }, (_, i) => 2024 - i);

interface Props {
  onResult: (result: PredictResponse) => void;
  selectedUnit?: string;
}

export default function PredictionForm({ onResult, selectedUnit }: Props) {
  const [species, setSpecies] = useState("Elk");
  const [unit, setUnit] = useState(selectedUnit || "5");
  const [year, setYear] = useState(2024);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Sync external unit selection
  if (selectedUnit && selectedUnit !== unit) {
    setUnit(selectedUnit);
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await predict({ species, hunt_unit: unit, year });
      onResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Species
        </label>
        <div className="flex gap-2">
          {SPECIES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSpecies(s)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
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

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Hunt Unit
        </label>
        <select
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-amber-500 focus:outline-none"
        >
          {UNITS.map((u) => (
            <option key={u} value={u}>
              Unit {u}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Year
        </label>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="w-full px-3 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-amber-500 focus:outline-none"
        >
          {YEARS.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
      >
        {loading ? "Predicting..." : "Predict Success Rate"}
      </button>

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </form>
  );
}
