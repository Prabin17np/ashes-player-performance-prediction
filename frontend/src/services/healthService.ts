import { apiClient, toApiError } from "./apiClient";
import type { HealthResponse } from "@/types/api";

export async function getHealth(): Promise<HealthResponse> {
  try {
    const { data } = await apiClient.get<HealthResponse>("/health");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}
