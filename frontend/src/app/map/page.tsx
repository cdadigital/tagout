"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const GMUMap = dynamic(() => import("@/components/GMUMap"), { ssr: false });

const SPECIES = ["Elk", "Deer"];
const YEARS = Array.from({ length: 22 }, (_, i) => 2024 - i);

export default function MapPage() {
  const [species, setSpecies] = useState("Elk");
  const [year, setYear] = useState(2024);

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Controls */}
      <div className="flex items-center gap-4 px-4 py-3 bg-gray-800 border-b border-gray-700">
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
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="px-3 py-1.5 bg-gray-700 text-white rounded text-sm border border-gray-600"
        >
          {YEARS.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <div className="flex-1" />
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-red-600" /> &lt;9%
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-orange-600" /> 9-12%
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-yellow-600" /> 12-15%
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-lime-600" /> 15-20%
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-green-600" /> 20%+
          </span>
        </div>
      </div>

      {/* Map */}
      <div className="flex-1">
        <GMUMap species={species} year={year} />
      </div>
    </div>
  );
}
