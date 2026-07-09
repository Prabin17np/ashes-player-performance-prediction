import { useState } from "react";
import { Wand2, Plus, X, ArrowUp, ArrowDown } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ASHES_TEAMS, ASHES_VENUES } from "@/utils/constants";
import type { FixtureDraft, SelectOption } from "@/types/domain";
import type { PlayerSummary } from "@/types/api";

interface QuickFillPanelProps {
  players: PlayerSummary[];
  onGenerate: (fixtures: FixtureDraft[]) => void;
}

/** Adds `days` to an ISO date string, returning another ISO date string. */
function addDays(iso: string, days: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Generates one entire series' fixtures for a single player: one match per
 * entry in `venues`, two innings each (1st + 3rd, since the model has no
 * way to know toss outcomes ahead of time), dates computed by walking
 * `startDate` forward through `gaps` (gaps[i] = days between match i and
 * match i+1, so gaps.length === venues.length - 1). */
function generateSeriesFixtures(params: {
  player: string;
  team: string;
  opponent: string;
  battingPosition: number | null;
  venues: string[];
  startDate: string;
  gaps: number[];
}): FixtureDraft[] {
  const { player, team, opponent, battingPosition, venues, startDate, gaps } = params;
  const fixtures: FixtureDraft[] = [];

  let currentDate = startDate;

  venues.forEach((venue, matchIndex) => {
    if (matchIndex > 0) {
      currentDate = addDays(currentDate, gaps[matchIndex - 1] ?? 14);
    }

    for (const inningsNumber of [1, 3]) {
      fixtures.push({
        id: crypto.randomUUID(),
        player,
        team,
        opponent,
        venue,
        match_date: currentDate,
        innings_number: inningsNumber,
        batting_position: battingPosition,
      });
    }
  });

  return fixtures;
}

export function QuickFillPanel({ players, onGenerate }: QuickFillPanelProps) {
  const [player, setPlayer] = useState("");
  const [team, setTeam] = useState("England");
  const [venues, setVenues] = useState<string[]>([]);
  const [venueToAdd, setVenueToAdd] = useState("");
  const [startDate, setStartDate] = useState("");
  const [gaps, setGaps] = useState<number[]>([]);
  const [battingPosition, setBattingPosition] = useState("");
  const [error, setError] = useState<string | null>(null);

  const playerOptions: SelectOption[] = players.map((p) => ({ value: p.name, label: p.name }));
  const teamOptions: SelectOption[] = ASHES_TEAMS.map((t) => ({ value: t, label: t }));
  const venueOptions: SelectOption[] = ASHES_VENUES.map((v) => ({ value: v, label: v }));
  const opponent = ASHES_TEAMS.find((t) => t !== team) ?? "";

  function addVenue() {
    if (!venueToAdd) return;
    setVenues((prev) => [...prev, venueToAdd]);
    setGaps((prev) => (venues.length > 0 ? [...prev, 14] : prev)); // one new gap per venue after the first
    setVenueToAdd("");
  }

  function removeVenue(index: number) {
    setVenues((prev) => prev.filter((_, i) => i !== index));
    setGaps((prev) => prev.filter((_, i) => i !== index - 1 && index > 0).slice(0, Math.max(venues.length - 2, 0)));
    // simplest safe rebuild: gaps length must always be venues.length - 1
    setGaps((prev) => {
      const next = [...prev];
      if (index > 0) next.splice(index - 1, 1);
      else if (next.length > 0) next.splice(0, 1);
      return next;
    });
  }

  function moveVenue(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= venues.length) return;
    setVenues((prev) => {
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function updateGap(gapIndex: number, value: number) {
    setGaps((prev) => {
      const next = [...prev];
      next[gapIndex] = value;
      return next;
    });
  }

  function handleGenerate() {
    if (!player || !team || !startDate) {
      setError("Choose a player, team, and start date to generate a series.");
      return;
    }
    if (venues.length === 0) {
      setError("Add at least one venue.");
      return;
    }
    setError(null);
    const fixtures = generateSeriesFixtures({
      player,
      team,
      opponent,
      battingPosition: battingPosition ? Number(battingPosition) : null,
      venues,
      startDate,
      gaps,
    });
    onGenerate(fixtures);
  }

  return (
    <Card className="p-6 sm:p-8">
      <div className="mb-5 flex items-start gap-3">
        <span className="mt-0.5 text-gold-500">
          <Wand2 size={18} />
        </span>
        <div>
          <h2 className="font-display text-lg font-semibold text-navy-700">
            Quick Fill a Whole Series
          </h2>
          <p className="mt-1 text-sm text-slate-450">
            Pick the player, team, and venues in order — set the gap between each match — and
            generate every fixture (1st + 3rd innings per match) in one go.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SearchableSelect
          label="Player"
          options={playerOptions}
          value={player}
          onChange={setPlayer}
          placeholder="Search for a player..."
        />
        <SearchableSelect
          label="Team"
          options={teamOptions}
          value={team}
          onChange={setTeam}
          placeholder="Select team"
        />
        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">
            Batting Position
          </label>
          <input
            type="number"
            min={1}
            max={11}
            placeholder="e.g. 4"
            value={battingPosition}
            onChange={(e) => setBattingPosition(e.target.value)}
            className="w-full rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">
            First Match Date
          </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400"
          />
        </div>
      </div>

      {/* Venue picker */}
      <div className="mt-6">
        <label className="mb-1.5 block text-sm font-medium text-navy-600">
          Add Venues (in match order)
        </label>
        <div className="flex gap-2">
          <div className="flex-1">
            <SearchableSelect
              label=""
              options={venueOptions}
              value={venueToAdd}
              onChange={setVenueToAdd}
              placeholder="Search venue..."
              allowFreeText
            />
          </div>
          <Button type="button" onClick={addVenue}>
            <Plus size={16} />
            Add
          </Button>
        </div>

        {venues.length > 0 && (
          <div className="mt-4 space-y-2">
            {venues.map((venue, i) => (
              <div key={`${venue}-${i}`} className="flex items-center gap-3">
                <div className="flex-1 rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm">
                  <span className="mr-2 font-mono text-slate-450">Test {i + 1}</span>
                  {venue}
                </div>

                {i > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-slate-450">Gap</span>
                    <input
                      type="number"
                      min={1}
                      value={gaps[i - 1] ?? 14}
                      onChange={(e) => updateGap(i - 1, Number(e.target.value))}
                      className="w-16 rounded-lg border border-navy-100 bg-white px-2 py-1.5 text-sm outline-none focus:border-gold-400"
                    />
                    <span className="text-xs text-slate-450">days</span>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => moveVenue(i, -1)}
                  disabled={i === 0}
                  className="text-slate-450 hover:text-navy-700 disabled:opacity-30"
                  aria-label="Move up"
                >
                  <ArrowUp size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => moveVenue(i, 1)}
                  disabled={i === venues.length - 1}
                  className="text-slate-450 hover:text-navy-700 disabled:opacity-30"
                  aria-label="Move down"
                >
                  <ArrowDown size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => removeVenue(i)}
                  className="text-slate-450 hover:text-red-600"
                  aria-label="Remove venue"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}

      <div className="mt-6">
        <Button onClick={handleGenerate} disabled={venues.length === 0}>
          <Wand2 size={16} />
          Generate {venues.length * 2} Fixtures
        </Button>
      </div>
    </Card>
  );
}