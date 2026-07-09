import { Database, Users, Cpu, Activity } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { Skeleton } from "@/components/ui/Skeleton";
import { usePlayers } from "@/hooks/usePlayers";
import { useHealth } from "@/hooks/useHealth";

const statusCopy: Record<string, { label: string; tone: string }> = {
  checking: { label: "Checking...", tone: "text-slate-450" },
  online: { label: "Online", tone: "text-emerald-600" },
  offline: { label: "Offline", tone: "text-red-600" },
};

export function DashboardCards() {
  const { players, isLoading } = usePlayers();
  const health = useHealth(30000);
  const status = statusCopy[health];

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <Card hoverElevate delay={0} className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-450">Historical Matches</p>
          <Database size={18} className="text-gold-500" />
        </div>
        <div className="mt-3 text-3xl font-display font-semibold text-navy-700">
          <AnimatedNumber value={6652} />
        </div>
        <p className="mt-1.5 text-xs text-slate-450">Test innings used for training</p>
      </Card>

      <Card hoverElevate delay={0.05} className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-450">Players</p>
          <Users size={18} className="text-gold-500" />
        </div>
        <div className="mt-3 text-3xl font-display font-semibold text-navy-700">
          {isLoading ? (
            <Skeleton className="h-9 w-16" />
          ) : (
            <AnimatedNumber value={players.length} />
          )}
        </div>
        <p className="mt-1.5 text-xs text-slate-450">Live from the players endpoint</p>
      </Card>

      <Card hoverElevate delay={0.1} className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-450">Prediction Model</p>
          <Cpu size={18} className="text-gold-500" />
        </div>
        <div className="mt-3 text-3xl font-display font-semibold text-navy-700">
          Random Forest
        </div>
        <p className="mt-1.5 text-xs text-slate-450">Trained on historical batting data</p>
      </Card>

      <Card hoverElevate delay={0.15} className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-450">API Status</p>
          <Activity size={18} className="text-gold-500" />
        </div>
        <div className={`mt-3 text-3xl font-display font-semibold ${status.tone}`}>
          {status.label}
        </div>
        <p className="mt-1.5 text-xs text-slate-450">Polled every 30 seconds</p>
      </Card>
    </div>
  );
}
