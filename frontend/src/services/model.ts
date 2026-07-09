import { apiClient, toApiError } from "./apiClient";
import type { ModelInfoResponse } from "@/types/api";

export async function getModelInfo(): Promise<ModelInfoResponse> {
  try {
    const { data } = await apiClient.get<ModelInfoResponse>("/model");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}