import { useEffect, useState } from "react";
import { getHealth } from "@/services/healthService";

export type HealthState = "checking" | "online" | "offline";

/** Polls GET /health once on mount (and optionally on an interval) to
 * drive the "API Status" dashboard card. Never throws -- any failure
 * to reach the backend is treated as "offline", not an error state,
 * since this is a passive status indicator, not a user action. */
export function useHealth(pollMs?: number): HealthState {
  const [state, setState] = useState<HealthState>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        const res = await getHealth();
        if (!cancelled) setState(res.status === "ok" ? "online" : "offline");
      } catch {
        if (!cancelled) setState("offline");
      }
    }

    check();
    const id = pollMs ? setInterval(check, pollMs) : undefined;
    return () => {
      cancelled = true;
      if (id) clearInterval(id);
    };
  }, [pollMs]);

  return state;
}
