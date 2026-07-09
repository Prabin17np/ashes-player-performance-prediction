import { useCallback, useState } from "react";
import { simulateSeries } from "@/services/simulationService";
import { ApiError } from "@/services/apiClient";
import type { SimulateRequest, SimulateResponse } from "@/types/api";

interface UseSimulationResult {
  result: SimulateResponse | null;
  isLoading: boolean;
  error: string | null;
  runSimulation: (payload: SimulateRequest) => Promise<void>;
  reset: () => void;
}

export function useSimulation(): UseSimulationResult {
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = useCallback(async (payload: SimulateRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await simulateSeries(payload);
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(
        err instanceof ApiError ? err.message : "The series simulation could not be completed."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isLoading, error, runSimulation, reset };
}
