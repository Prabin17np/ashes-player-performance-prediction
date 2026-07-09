import { useCallback, useState } from "react";
import { predictInnings } from "@/services/predictionService";
import { ApiError } from "@/services/apiClient";
import type { PredictRequest, PredictResponse } from "@/types/api";

interface UsePredictionResult {
  result: PredictResponse | null;
  isLoading: boolean;
  error: string | null;
  predict: (payload: PredictRequest) => Promise<void>;
  reset: () => void;
}

export function usePrediction(): UsePredictionResult {
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const predict = useCallback(async (payload: PredictRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await predictInnings(payload);
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(
        err instanceof ApiError ? err.message : "No prediction could be generated."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isLoading, error, predict, reset };
}
