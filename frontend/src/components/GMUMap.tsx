"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import { getGmu, predictMap, UnitScore } from "@/lib/api";
import type L from "leaflet";
import "leaflet/dist/leaflet.css";

function getColor(pct: number): string {
  if (pct >= 20) return "#16a34a"; // green-600
  if (pct >= 15) return "#65a30d"; // lime-600
  if (pct >= 12) return "#ca8a04"; // yellow-600
  if (pct >= 9) return "#ea580c"; // orange-600
  return "#dc2626"; // red-600
}

interface Props {
  species: string;
  year: number;
  onUnitClick?: (unitId: string) => void;
}

export default function GMUMap({ species, year, onUnitClick }: Props) {
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(
    null
  );
  const [scores, setScores] = useState<Record<string, UnitScore>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [geo, mapScores] = await Promise.all([
          getGmu(),
          predictMap(species, year),
        ]);
        setGeojson(geo);
        const scoreMap: Record<string, UnitScore> = {};
        mapScores.forEach((s) => (scoreMap[s.hunt_unit] = s));
        setScores(scoreMap);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to load map";
        setError(msg);
        console.error("Failed to load map data:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [species, year]);

  const style = (feature: GeoJSON.Feature | undefined) => {
    if (!feature) return {};
    const unitName = feature.properties?.NAME;
    const score = scores[unitName];
    const pct = score?.predicted_success_pct || 0;
    return {
      fillColor: getColor(pct),
      weight: 2,
      opacity: 1,
      color: "#374151",
      fillOpacity: 0.7,
    };
  };

  const onEachFeature = (
    feature: GeoJSON.Feature,
    layer: L.Layer
  ) => {
    const unitName = feature.properties?.NAME;
    const score = scores[unitName];
    if (score) {
      layer.bindTooltip(
        `<strong>Unit ${unitName}</strong><br/>` +
          `Predicted: ${score.predicted_success_pct}%<br/>` +
          `Historical: ${score.historical_avg ?? "N/A"}%`,
        { sticky: true }
      );
    }
    layer.on("click", () => {
      if (onUnitClick) onUnitClick(unitName);
    });
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        Loading map...
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center text-red-400 text-sm px-4 text-center">
        {error}
      </div>
    );
  }

  return (
    <MapContainer
      center={[47.6, -116.2]}
      zoom={8}
      className="h-full w-full rounded-lg"
      style={{ background: "#1f2937" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {geojson && (
        <GeoJSON
          key={`${species}-${year}`}
          data={geojson}
          style={style}
          onEachFeature={onEachFeature}
        />
      )}
    </MapContainer>
  );
}
