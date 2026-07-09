import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { PlayerCard } from "./PlayerCard";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import type { PlayerSummary } from "@/types/api";

interface PlayerGridProps {
  players: PlayerSummary[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function PlayerGrid({ players, isLoading, error, onRetry }: PlayerGridProps) {
  const [query, setQuery] = useState("");
  const [team, setTeam] = useState<string>("all");

  const teams = useMemo(() => {
    const unique = Array.from(new Set(players.map((p) => p.team))).sort();
    return unique;
  }, [players]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return players.filter((p) => {
      const matchesQuery = !q || p.name.toLowerCase().includes(q);
      const matchesTeam = team === "all" || p.team === team;
      return matchesQuery && matchesTeam;
    });
  }, [players, query, team]);

  if (error) {
    return <ErrorBanner message={error} onRetry={onRetry} />;
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-450" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search players..."
            className="w-full rounded-xl border border-navy-100 bg-white py-2.5 pl-10 pr-3.5 text-sm outline-none focus:border-gold-400"
          />
        </div>
        <select
          value={team}
          onChange={(e) => setTeam(e.target.value)}
          className="rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400 sm:w-56"
        >
          <option value="all">All teams</option>
          {teams.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-navy-100 bg-white p-10 text-center">
          <p className="text-sm text-slate-450">No players match your search.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p, i) => (
            <PlayerCard key={p.name} player={p} delay={Math.min(i * 0.03, 0.3)} />
          ))}
        </div>
      )}
    </div>
  );
}
