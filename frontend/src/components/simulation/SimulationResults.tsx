import { motion } from "framer-motion";
import { Trophy, Users2, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { PredictedRunsBarChart } from "@/components/charts/PredictedRunsBarChart";

import { PlayerComparisonChart } from "@/components/charts/PlayerComparisonChart";
import { ModelInfoCard } from "@/components/model/ModelInfoCard";
import type { SimulateResponse } from "@/types/api";

interface SimulationResultsProps {
  result: SimulateResponse;
}

export function SimulationResults({ result }: SimulationResultsProps) {
  const { predictions, player_summaries} = result;

  const topScorer = player_summaries.reduce(
    (best, p) => (p.total_runs > (best?.total_runs ?? -Infinity) ? p : best),
    player_summaries[0]
  );

  const grandTotal = player_summaries.reduce(
  (sum, player) => sum + player.total_runs,
  0
);
  const avgRuns = predictions.length ? grandTotal / predictions.length : 0;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <Card hoverElevate className="p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-450">Highest Scorer</p>
            <Trophy size={18} className="text-gold-500" />
          </div>
          <p className="mt-3 font-display text-2xl font-semibold text-navy-700">
            {topScorer?.player ?? "—"}
          </p>
          <p className="mt-1 text-sm text-slate-450">
            <AnimatedNumber value={topScorer?.total_runs ?? 0} decimals={1} className="text-navy-600" />{" "}
            runs across {topScorer?.innings ?? 0} innings
          </p>
        </Card>

        <Card hoverElevate delay={0.05} className="p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-450">Total Series Runs</p>
            <Users2 size={18} className="text-gold-500" />
          </div>
          <p className="mt-3 font-display text-3xl font-semibold text-navy-700">
            <AnimatedNumber value={grandTotal} decimals={0} />
          </p>
          <p className="mt-1 text-sm text-slate-450">across both teams</p>
        </Card>

        <Card hoverElevate delay={0.1} className="p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-450">Average per Innings</p>
            <TrendingUp size={18} className="text-gold-500" />
          </div>
          <p className="mt-3 font-display text-3xl font-semibold text-navy-700">
            <AnimatedNumber value={avgRuns} decimals={1} />
          </p>
          <p className="mt-1 text-sm text-slate-450">{predictions.length} innings simulated</p>
        </Card>
      </div>
      
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h3 className="mb-4 font-display text-lg font-semibold text-navy-700">
            Predicted Runs by Innings
          </h3>
          <PredictedRunsBarChart predictions={predictions} />
        </Card>
        <ModelInfoCard />
      </div>
      

      <Card className="p-6">
        <h3 className="mb-4 font-display text-lg font-semibold text-navy-700">
          Player Comparison
        </h3>
        <PlayerComparisonChart playerSummaries={player_summaries} />
      </Card>
      

      <Card className="overflow-hidden">
        <div className="border-b border-navy-50 px-6 py-4">
          <h3 className="font-display text-lg font-semibold text-navy-700">Player Summary</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-navy-50 text-left text-xs uppercase tracking-wide text-slate-450">
                <th className="px-6 py-3">Player</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">Innings</th>
                <th className="px-4 py-3">Total Runs</th>
                <th className="px-4 py-3">Average</th>
                <th className="px-4 py-3">High Score</th>
                <th className="px-4 py-3">50s / 100s</th>
              </tr>
            </thead>
            <tbody>
              {player_summaries.map((p, i) => (
                <motion.tr
                  key={p.player}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: Math.min(i * 0.04, 0.4) }}
                  className={`border-b border-navy-50 last:border-0 ${
                    p.player === topScorer?.player ? "bg-gold-50/60" : ""
                  }`}
                >
                  <td className="px-6 py-3 font-medium text-navy-700">
                    <span className="flex items-center gap-2">
                      {p.player}
                      {p.player === topScorer?.player && (
                        <Badge tone="gold">Top scorer</Badge>
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-450">{p.team}</td>
                  <td className="px-4 py-3 font-mono text-navy-600">{p.innings}</td>
                  <td className="px-4 py-3 font-mono text-navy-700">{p.total_runs.toFixed(1)}</td>
                  <td className="px-4 py-3 font-mono text-navy-600">{p.batting_average.toFixed(1)}</td>
                  <td className="px-4 py-3 font-mono text-navy-600">{p.highest_score.toFixed(1)}</td>
                  <td className="px-4 py-3 font-mono text-navy-600">
                    {p.fifties} / {p.centuries}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
