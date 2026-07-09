// Mirrors backend/app/schemas/player.py
export interface PlayerSummary {
  name: string;
  team: string;
}

// Mirrors backend/app/schemas/prediction.py -> PredictRequest
export interface PredictRequest {
  player: string;
  team: string;
  opponent: string;
  venue: string;
  match_date: string; // ISO 8601 date, e.g. "2027-06-18"
  innings_number: number;
  batting_position?: number | null;
}

// Mirrors backend/app/schemas/prediction.py -> PredictResponse
export interface PredictResponse {
  player: string;
  team: string;
  opponent: string;
  venue: string;
  match_date: string;
  innings_number: number;
  batting_position?: number | null;
  predicted_runs: number;
  confidence?: number | null;
  features?: Record<string, unknown> | null;
}

// Mirrors backend/app/schemas/simulation.py -> FixtureRequest
export interface FixtureRequest {
  player: string;
  team: string;
  opponent: string;
  venue: string;
  match_date: string;
  innings_number: number;
  batting_position?: number | null;
}

// Mirrors backend/app/schemas/simulation.py -> SimulateRequest
export interface SimulateRequest {
  fixtures: FixtureRequest[];
  allow_debutants?: boolean | null;
}

// Mirrors backend/app/schemas/simulation.py -> PredictionResultSchema
export interface PredictionResultSchema {
  player: string;
  team: string;
  opponent: string;
  venue: string;
  match_date: string;
  innings_number: number;
  batting_position?: number | null;
  predicted_runs: number;
}

// Mirrors backend/app/schemas/simulation.py -> PlayerSeriesSummarySchema
export interface PlayerSeriesSummarySchema {
  player: string;
  team: string;
  matches: number;
  innings: number;
  total_runs: number;
  batting_average: number;
  highest_score: number;
  lowest_score: number;
  fifties: number;
  centuries: number;
  predicted_scores: number[];
}

// Mirrors backend/app/schemas/simulation.py -> SimulateResponse
export interface SimulateResponse {
  predictions: PredictionResultSchema[];
  player_summaries: PlayerSeriesSummarySchema[];
  team_totals: Record<string, number>;
}

export interface HealthResponse {
  status: string;
}

// Shape of FastAPI's default error body, produced by the backend's
// registered exception handlers (422 / 500 / 503) -- see
// app/utils/exceptions.py. Also covers the plain {"detail": [...]}
// shape FastAPI itself emits for request-schema validation errors.
export interface ApiErrorBody {
  detail?: string | { msg?: string }[];
}

// Mirrors backend/app/schemas/model_info.py -> ModelInfoResponse
export interface ModelInfoResponse {
  model_name: string;
  algorithm: string;
  training_samples: number;
  features: number;
  cv_mae: number;
  cv_rmse: number;
  cv_r2: number;
  test_mae: number;
  test_rmse: number;
  test_r2: number;
}