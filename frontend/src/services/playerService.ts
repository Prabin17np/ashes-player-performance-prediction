import { apiClient, toApiError } from "./apiClient";
import type { PlayerSummary } from "@/types/api";

export async function getPlayers(): Promise<PlayerSummary[]> {
  try {
    const { data } = await apiClient.get<PlayerSummary[]>("/players");
    return data;
  } catch (error) {
    throw toApiError(error);
  }
}
