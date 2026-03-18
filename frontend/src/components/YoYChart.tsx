"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { getHarvestStats, HarvestStat } from "@/lib/api";

interface Props {
  species: string;
  huntUnit: string;
  predictedPct: number;
  predictedYear: number;
  weaponType?: string;
}

interface ChartRow {
  year: string;
  fullYear: number;
  pct: number;
  isPrediction: boolean;
}

export default function YoYChart({ species, huntUnit, predictedPct, predictedYear, weaponType }: Props) {
  const [data, setData] = useState<ChartRow[]>([]);
  const [loading, setLoading] = useState(true);

  const showPrediction = !weaponType || weaponType === "All Weapons Combined";

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const stats: HarvestStat[] = await getHarvestStats(species, huntUnit, weaponType);
        const recent = stats
          .filter((s) => s.success_pct !== null)
          .sort((a, b) => a.season_year - b.season_year)
          .slice(-10);

        const rows: ChartRow[] = recent.map((s) => ({
          year: `'${String(s.season_year).slice(-2)}`,
          fullYear: s.season_year,
          pct: Number((s.success_pct ?? 0).toFixed(1)),
          isPrediction: false,
        }));

        if (showPrediction) {
          rows.push({
            year: `'${String(predictedYear).slice(-2)}`,
            fullYear: predictedYear,
            pct: Number(predictedPct.toFixed(1)),
            isPrediction: true,
          });
        }

        setData(rows);
      } catch (err) {
        console.error("Failed to load YoY stats:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [species, huntUnit, predictedPct, predictedYear, weaponType, showPrediction]);

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-gray-700 border-t-gray-500 rounded-full animate-spin" />
      </div>
    );
  }
  if (!data.length) {
    return <div className="text-gray-600 text-xs py-8 text-center">No historical data</div>;
  }

  const historical = data.filter((d) => !d.isPrediction);
  const avg = historical.length > 0
    ? historical.reduce((sum, d) => sum + d.pct, 0) / historical.length
    : 0;

  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barCategoryGap="15%">
          <XAxis
            dataKey="year"
            stroke="#4b5563"
            tick={{ fontSize: 10, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            stroke="#4b5563"
            tick={{ fontSize: 10, fill: "#6b7280" }}
            width={32}
            axisLine={false}
            tickLine={false}
            unit="%"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(17, 24, 39, 0.95)",
              border: "1px solid rgba(75, 85, 99, 0.4)",
              borderRadius: "12px",
              fontSize: "12px",
              boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
              padding: "8px 12px",
            }}
            labelStyle={{ color: "#9ca3af", marginBottom: "2px" }}
            formatter={(value: unknown) => [`${value}%`, "Success Rate"]}
            labelFormatter={(label: unknown) => {
              const clean = String(label).replace("'", "");
              return `20${clean} Season`;
            }}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          {avg > 0 && (
            <ReferenceLine
              y={Number(avg.toFixed(1))}
              stroke="#4b5563"
              strokeDasharray="4 4"
              label={{
                value: `${avg.toFixed(0)}% avg`,
                position: "right",
                fill: "#6b7280",
                fontSize: 9,
              }}
            />
          )}
          <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.isPrediction ? "#d97706" : "#374151"}
                fillOpacity={entry.isPrediction ? 1 : 0.8}
                stroke={entry.isPrediction ? "#f59e0b" : "transparent"}
                strokeWidth={entry.isPrediction ? 2 : 0}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
