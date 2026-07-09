import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PlayerSeriesSummarySchema } from "@/types/api";

interface PlayerComparisonChartProps {
  playerSummaries: PlayerSeriesSummarySchema[];
}

const LINE_COLORS = ["#C79A3C", "#16335C", "#7C97C1", "#846222", "#3F5D8E", "#DDBB68"];

export function PlayerComparisonChart({ playerSummaries }: PlayerComparisonChartProps) {
  const top = playerSummaries.slice(0, 6);
  const maxInnings = Math.max(0, ...top.map((p) => p.predicted_scores.length));

  const data = Array.from({ length: maxInnings }, (_, i) => {
    const row: Record<string, number | string> = { innings: `Inn. ${i + 1}` };
    top.forEach((p) => {
      row[p.player] = p.predicted_scores[i] ?? null as unknown as number;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#EEF2F8" />
        <XAxis dataKey="innings" tick={{ fontSize: 11, fill: "#5B6472" }} axisLine={{ stroke: "#DAE3F0" }} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: "#5B6472" }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #EEF2F8", fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {top.map((p, i) => (
          <Line
            key={p.player}
            type="monotone"
            dataKey={p.player}
            stroke={LINE_COLORS[i % LINE_COLORS.length]}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
