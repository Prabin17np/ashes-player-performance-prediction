import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { PlayerSummary } from "@/types/api";

interface PlayerCardProps {
  player: PlayerSummary;
  delay?: number;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const teamTone = (team: string): "gold" | "navy" =>
  team.toLowerCase().includes("england") ? "navy" : "gold";

export function PlayerCard({ player, delay = 0 }: PlayerCardProps) {
  return (
    <Card hoverElevate delay={delay} className="p-5">
      <div className="flex items-center gap-3.5">
        <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-navy-50 font-display text-sm font-semibold text-navy-600">
          {initials(player.name)}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-navy-700">{player.name}</p>
          <p className="truncate text-xs text-slate-450">{player.team}</p>
        </div>
      </div>
      <div className="mt-4">
        <Badge tone={teamTone(player.team)}>{player.team}</Badge>
      </div>
    </Card>
  );
}
