import { PredictionForm } from "@/components/prediction/PredictionForm";
import { PredictionResultCard } from "@/components/prediction/PredictionResultCard";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Card } from "@/components/ui/Card";
import { usePlayers } from "@/hooks/usePlayers";
import { usePrediction } from "@/hooks/usePrediction";

export function PredictPage() {
  const { players, isLoading: playersLoading, error: playersError, reload } = usePlayers();
  const { result, isLoading, error, predict } = usePrediction();

  return (
    <div className="mx-auto max-w-5xl px-6 py-14">
      <header className="mb-10">
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-gold-600">
          Single Innings
        </p>
        <h1 className="font-display text-3xl font-semibold text-navy-700 sm:text-4xl">
          Predict Player Runs
        </h1>
        <p className="mt-2 max-w-xl text-sm text-slate-450">
          Fill in the matchup details below to get a predicted runs total for one innings.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_1fr]">
        <Card className="p-6 sm:p-8">
          {playersError ? (
            <ErrorBanner message={playersError} onRetry={reload} />
          ) : (
            <PredictionForm
              players={players}
              isSubmitting={isLoading || playersLoading}
              onSubmit={predict}
            />
          )}
        </Card>

        <div className="space-y-5">
          {isLoading && (
            <Card className="p-8">
              <ProgressBar label="Running the model..." />
            </Card>
          )}

          {!isLoading && error && <ErrorBanner message={error} />}

          {!isLoading && !error && result && <PredictionResultCard result={result} />}

          {!isLoading && !error && !result && (
            <div className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-navy-100 bg-white/60 p-10 text-center">
              <p className="text-sm text-slate-450">
                Your prediction will appear here once you submit the form.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
