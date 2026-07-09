import { useState } from "react";
import { Plus, Play, Trash } from "lucide-react";
import { FixtureRow } from "@/components/simulation/FixtureRow";
import { QuickFillPanel } from "@/components/simulation/QuickFillPanel";
import { SimulationResults } from "@/components/simulation/SimulationResults";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { usePlayers } from "@/hooks/usePlayers";
import { useSimulation } from "@/hooks/useSimulation";
import type { FixtureDraft } from "@/types/domain";
import type { SelectOption } from "@/types/domain";

function newFixture(): FixtureDraft {
  return {
    id: crypto.randomUUID(),
    player: "",
    team: "",
    opponent: "",
    venue: "",
    match_date: "",
    innings_number: 1,
    batting_position: null,
  };
}

export function SimulatePage() {
  const { players } = usePlayers();
  const { result, isLoading, error, runSimulation, reset } = useSimulation();
  const [fixtures, setFixtures] = useState<FixtureDraft[]>([]);
  const [allowDebutants, setAllowDebutants] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  const playerOptions: SelectOption[] = players.map((p) => ({ value: p.name, label: p.name }));

  function addFixture() {
    setFixtures((f) => [...f, newFixture()]);
  }

  function removeFixture(id: string) {
    setFixtures((f) => f.filter((fx) => fx.id !== id));
  }

  function updateFixture(id: string, patch: Partial<FixtureDraft>) {
    setFixtures((f) => f.map((fx) => (fx.id === id ? { ...fx, ...patch } : fx)));
  }

  function handleQuickFill(generated: FixtureDraft[]) {
    setFixtures(generated);
    setFormError(null);
  }

  async function handleRun() {
    if (fixtures.length === 0) {
      setFormError("Add at least one fixture, or use Quick Fill, before running the simulation.");
      return;
    }
    const incomplete = fixtures.some(
      (fx) => !fx.player || !fx.team || !fx.opponent || !fx.venue || !fx.match_date
    );
    if (incomplete) {
      setFormError("Please complete every field for each fixture before running the simulation.");
      return;
    }
    setFormError(null);
    await runSimulation({
      fixtures: fixtures.map(({ id, ...rest }) => rest),
      allow_debutants: allowDebutants,
    });
  }

  function handleReset() {
    setFixtures([]);
    reset();
    setFormError(null);
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-14">
      <header className="mb-10">
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-gold-600">
          Full Series
        </p>
        <h1 className="font-display text-3xl font-semibold text-navy-700 sm:text-4xl">
          Simulate a Series
        </h1>
        <p className="mt-2 max-w-xl text-sm text-slate-450">
          Quick fill a whole series for one player, or add fixtures one at a time — then run
          them all through the model at once.
        </p>
      </header>

      {!result && (
        <>
          <div className="mb-8">
            <QuickFillPanel players={players} onGenerate={handleQuickFill} />
          </div>

          {fixtures.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-navy-100 bg-white/60 p-10 text-center">
              <p className="text-sm text-slate-450">
                No fixtures yet. Use Quick Fill above, or add one manually below.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {fixtures.map((fixture, i) => (
                <FixtureRow
                  key={fixture.id}
                  index={i}
                  fixture={fixture}
                  playerOptions={playerOptions}
                  onChange={updateFixture}
                  onRemove={removeFixture}
                />
              ))}
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={addFixture}>
                <Plus size={16} />
                Add Fixture
              </Button>
              {fixtures.length > 0 && (
                <Button
                  variant="ghost"
                  onClick={() => removeFixture(fixtures[fixtures.length - 1].id)}
                >
                  <Trash size={16} />
                  Remove Fixture
                </Button>
              )}
            </div>

            <label className="flex items-center gap-2 text-sm text-navy-600">
              <input
                type="checkbox"
                checked={allowDebutants}
                onChange={(e) => setAllowDebutants(e.target.checked)}
                className="h-4 w-4 rounded border-navy-200 text-gold-600 focus:ring-gold-400"
              />
              Allow debutants
            </label>
          </div>

          {formError && (
            <div className="mt-5">
              <ErrorBanner message={formError} />
            </div>
          )}

          <div className="mt-8">
            <Button size="lg" isLoading={isLoading} onClick={handleRun} className="min-w-[200px]">
              <Play size={16} />
              Run Simulation
            </Button>
          </div>

          {isLoading && (
            <Card className="mt-6 p-8">
              <ProgressBar label="Simulating the series, innings by innings..." />
            </Card>
          )}

          {!isLoading && error && (
            <div className="mt-6">
              <ErrorBanner message={error} />
            </div>
          )}
        </>
      )}

      {result && (
        <div>
          <div className="mb-6 flex justify-end">
            <Button variant="secondary" onClick={handleReset}>
              Start a new simulation
            </Button>
          </div>
          <SimulationResults result={result} />
        </div>
      )}
    </div>
  );
}
