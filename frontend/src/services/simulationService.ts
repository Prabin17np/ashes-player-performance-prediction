import { apiClient, toApiError } from "./apiClient";
import type { SimulateRequest, SimulateResponse } from "@/types/api";

export async function simulateSeries(payload: SimulateRequest): Promise<SimulateResponse> {
  try {
    const { data } = await apiClient.post<SimulateResponse>("/simulate", payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}
