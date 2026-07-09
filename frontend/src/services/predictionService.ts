import { apiClient, toApiError } from "./apiClient";
import type { PredictRequest, PredictResponse } from "@/types/api";

export async function predictInnings(payload: PredictRequest): Promise<PredictResponse> {
  try {
    const { data } = await apiClient.post<PredictResponse>("/predict", payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}
