import type { FixtureRequest } from "./api";

/** A fixture row in the Series Simulation builder, before submission.
 * Carries a client-only `id` so React can key/remove rows; stripped
 * before the request is sent to POST /simulate. */
export interface FixtureDraft extends FixtureRequest {
  id: string;
}

export interface SelectOption {
  value: string;
  label: string;
}
