import axios, { AxiosError } from "axios";
import type { ApiErrorBody } from "@/types/api";

// In dev, requests go to /api/* and Vite's proxy (see vite.config.ts)
// forwards them to the FastAPI backend, avoiding CORS entirely.
// In production, point VITE_API_BASE_URL at the deployed backend root
// (e.g. https://api.example.com) and requests will hit it directly.
const baseURL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export const apiClient = axios.create({
  baseURL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

/** A normalized, user-safe error message extracted from any Axios/API
 * failure. Never surfaces raw backend stack traces or FastAPI's own
 * validation-error object shape -- only a plain sentence. */
export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<ApiErrorBody>;

    if (!err.response) {
      return new ApiError(
        "Could not reach the prediction service. Check your connection and try again."
      );
    }

    const { status, data } = err.response;
    const detail = data?.detail;

    if (typeof detail === "string" && detail.trim().length > 0) {
      return new ApiError(detail, status);
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const msgs = detail.map((d) => d.msg).filter(Boolean).join(" ");
      return new ApiError(msgs || "The request could not be processed.", status);
    }

    if (status === 503) {
      return new ApiError(
        "The prediction model is temporarily unavailable. Please try again shortly.",
        status
      );
    }

    if (status && status >= 500) {
      return new ApiError("Something went wrong on our end. Please try again.", status);
    }

    return new ApiError("The request could not be processed. Please check your input.", status);
  }

  return new ApiError("An unexpected error occurred.");
}
