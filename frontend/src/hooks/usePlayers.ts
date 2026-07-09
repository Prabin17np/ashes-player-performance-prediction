import { useCallback, useEffect, useState } from "react";
import { getPlayers } from "@/services/playerService";
import type { PlayerSummary } from "@/types/api";
import { ApiError } from "@/services/apiClient";

interface UsePlayersResult {
  players: PlayerSummary[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function usePlayers(): UsePlayersResult {
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    getPlayers()
      .then((data) => {
        if (!cancelled) setPlayers(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Could not load players.");
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [nonce]);

  return { players, isLoading, error, reload };
}
