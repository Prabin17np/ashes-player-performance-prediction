import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface TeamTotalChartProps {
  teamTotals: Record<string, number>;
}

export function TeamTotalChart({ teamTotals }: TeamTotalChartProps) {
  const data = Object.entries(teamTotals).map(([team, total]) => ({
    team,
    total: Math.round(total * 100) / 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
        <CartesianGrid horizontal={false} stroke="#EEF2F8" />
        <XAxis type="number" tick={{ fontSize: 11, fill: "#5B6472" }} axisLine={false} tickLine={false} />
        <YAxis
          type="category"
          dataKey="team"
          tick={{ fontSize: 12, fill: "#16335C", fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
          width={90}
        />
        <Tooltip
          contentStyle={{ borderRadius: 12, border: "1px solid #EEF2F8", fontSize: 12 }}
          formatter={(value: number) => [`${value} runs`, "Team total"]}
        />
        <Bar dataKey="total" fill="#16335C" radius={[0, 6, 6, 0]} maxBarSize={28} />
      </BarChart>
    </ResponsiveContainer>
  );
}
