import { motion } from "framer-motion";
import { MapPin, Shield, Swords } from "lucide-react";
import { ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { CricketBatIcon } from "@/components/ui/CricketBatIcon";
import type { PredictResponse } from "@/types/api";

interface PredictionResultCardProps {
  result: PredictResponse;
}

function confidenceTone(confidence?: number | null): "gold" | "green" | "gray" {
  if (confidence == null) return "gray";
  if (confidence >= 0.75) return "green";
  return "gold";
}

export function PredictionResultCard({ result }: PredictionResultCardProps) {
  return (
    <Card className="overflow-hidden">
      <div className="bg-navy-700 px-6 py-5 text-white">
        <p className="flex items-center gap-1.5 text-xs uppercase tracking-[0.18em] text-gold-300">
          <CricketBatIcon size={14} />
          Predicted Runs
        </p>
        <div className="mt-1.5 flex items-baseline gap-2">
          <AnimatedNumber
            value={result.predicted_runs}
            decimals={2}
            className="text-4xl font-semibold text-white"
          />
          <span className="text-sm text-navy-200">runs</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 p-6 sm:grid-cols-2">
        <Detail icon={<Swords size={15} />} label="Player" value={result.player} />
        <Detail icon={<Shield size={15} />} label="Opponent" value={result.opponent} />
        <Detail icon={<MapPin size={15} />} label="Venue" value={result.venue} />
        <Detail
          icon={<Shield size={15} />}
          label="Team"
          value={result.team}
        />
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="flex flex-wrap items-center gap-2 border-t border-navy-50 px-6 py-4"
      >
        <Badge tone="navy">Innings {result.innings_number}</Badge>
        {result.batting_position != null && (
          <Badge tone="navy">Batting at No. {result.batting_position}</Badge>
        )}
        <Badge tone="navy">{result.match_date}</Badge>
        {result.confidence != null && (
          <Badge tone={confidenceTone(result.confidence)}>
            {Math.round(result.confidence * 100)}% confidence
          </Badge>
        )}
      </motion.div>
    </Card>
  );
}

function Detail({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 text-gold-500">{icon}</span>
      <div>
        <p className="text-xs text-slate-450">{label}</p>
        <p className="text-sm font-medium text-navy-700">{value}</p>
      </div>
    </div>
  );
}
