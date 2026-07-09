import { Trash2 } from "lucide-react";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ASHES_TEAMS, ASHES_VENUES } from "@/utils/constants";
import type { FixtureDraft } from "@/types/domain";
import type { SelectOption } from "@/types/domain";

interface FixtureRowProps {
  index: number;
  fixture: FixtureDraft;
  playerOptions: SelectOption[];
  onChange: (id: string, patch: Partial<FixtureDraft>) => void;
  onRemove: (id: string) => void;
}

export function FixtureRow({ index, fixture, playerOptions, onChange, onRemove }: FixtureRowProps) {
  const teamOptions: SelectOption[] = ASHES_TEAMS.map((t) => ({ value: t, label: t }));
  const opponentOptions: SelectOption[] = ASHES_TEAMS.filter((t) => t !== fixture.team).map((t) => ({
    value: t,
    label: t,
  }));
  const venueOptions: SelectOption[] = ASHES_VENUES.map((v) => ({ value: v, label: v }));

  return (
    <div className="rounded-2xl border border-navy-50 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-450">
          Fixture {index + 1}
        </p>
        <button
          type="button"
          onClick={() => onRemove(fixture.id)}
          className="text-slate-450 hover:text-red-600"
          aria-label={`Remove fixture ${index + 1}`}
        >
          <Trash2 size={16} />
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SearchableSelect
          label="Player"
          options={playerOptions}
          value={fixture.player}
          onChange={(v) => onChange(fixture.id, { player: v })}
          placeholder="Search player..."
        />
        <SearchableSelect
          label="Team"
          options={teamOptions}
          value={fixture.team}
          onChange={(v) => onChange(fixture.id, { team: v })}
          placeholder="Select team"
        />
        <SearchableSelect
          label="Opponent"
          options={opponentOptions}
          value={fixture.opponent}
          onChange={(v) => onChange(fixture.id, { opponent: v })}
          placeholder="Select opponent"
        />
        <SearchableSelect
          label="Venue"
          options={venueOptions}
          value={fixture.venue}
          onChange={(v) => onChange(fixture.id, { venue: v })}
          placeholder="Search venue..."
          allowFreeText
        />

        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">
            Batting Position
          </label>
          <input
            type="number"
            min={1}
            max={11}
            value={fixture.batting_position ?? ""}
            onChange={(e) =>
              onChange(fixture.id, {
                batting_position: e.target.value ? Number(e.target.value) : null,
              })
            }
            className="w-full rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">
            Innings Number
          </label>
          <select
            value={fixture.innings_number}
            onChange={(e) => onChange(fixture.id, { innings_number: Number(e.target.value) })}
            className="w-full rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400"
          >
            <option value={1}>1st Innings</option>
            <option value={2}>2nd Innings</option>
            <option value={3}>3rd Innings</option>
            <option value={4}>4th Innings</option>
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">Match Date</label>
          <input
            type="date"
            value={fixture.match_date}
            onChange={(e) => onChange(fixture.id, { match_date: e.target.value })}
            className="w-full rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400"
          />
        </div>
      </div>
    </div>
  );
}
