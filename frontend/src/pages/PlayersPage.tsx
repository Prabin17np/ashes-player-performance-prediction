import { usePlayers } from "@/hooks/usePlayers";
import { PlayerGrid } from "@/components/players/PlayerGrid";

export function PlayersPage() {
  const { players, isLoading, error, reload } = usePlayers();

  return (
    <div className="mx-auto max-w-6xl px-6 py-14">
      <header className="mb-10">
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-gold-600">
          Historical Dataset
        </p>
        <h1 className="font-display text-3xl font-semibold text-navy-700 sm:text-4xl">Players</h1>
        <p className="mt-2 max-w-xl text-sm text-slate-450">
          Every player available in the historical dataset, ready to use in a prediction or
          series simulation.
        </p>
      </header>

      <PlayerGrid players={players} isLoading={isLoading} error={error} onRetry={reload} />
    </div>
  );
}
