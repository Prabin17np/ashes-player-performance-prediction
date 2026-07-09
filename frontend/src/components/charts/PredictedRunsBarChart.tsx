import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PredictionResultSchema } from "@/types/api";

interface PredictedRunsBarChartProps {
  predictions: PredictionResultSchema[];
}

export function PredictedRunsBarChart({ predictions }: PredictedRunsBarChartProps) {
  const data = predictions.map((p, i) => ({
    label: p.player.split(" ").slice(-1)[0],
    runs: Math.round(p.predicted_runs * 100) / 100,
    innings: i + 1,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#EEF2F8" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "#5B6472" }}
          axisLine={{ stroke: "#DAE3F0" }}
          tickLine={false}
        />
        <YAxis tick={{ fontSize: 11, fill: "#5B6472" }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{
            borderRadius: 12,
            border: "1px solid #EEF2F8",
            fontSize: 12,
          }}
          formatter={(value: number) => [`${value} runs`, "Predicted"]}
        />
        <Bar dataKey="runs" fill="#C79A3C" radius={[6, 6, 0, 0]} maxBarSize={36} />
      </BarChart>
    </ResponsiveContainer>
  );
}
