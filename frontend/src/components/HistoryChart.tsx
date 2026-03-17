"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { getHarvestStats, HarvestStat } from "@/lib/api";

interface Props {
  species: string;
  huntUnit: string;
}

export default function HistoryChart({ species, huntUnit }: Props) {
  const [data, setData] = useState<HarvestStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const stats = await getHarvestStats(species, huntUnit);
        setData(stats);
      } catch (err) {
        console.error("Failed to load stats:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [species, huntUnit]);

  if (loading) return <div className="text-gray-400 text-sm">Loading...</div>;
  if (!data.length) return <div className="text-gray-400 text-sm">No data</div>;

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="season_year"
            stroke="#9ca3af"
            tick={{ fontSize: 11 }}
          />
          <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "8px",
            }}
            labelStyle={{ color: "#d1d5db" }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="success_pct"
            stroke="#d97706"
            strokeWidth={2}
            dot={{ fill: "#d97706", r: 3 }}
            name="Success %"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
