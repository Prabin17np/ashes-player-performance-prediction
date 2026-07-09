import { Controller, useForm } from "react-hook-form";
import { Search, Eraser } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { ASHES_TEAMS, ASHES_VENUES } from "@/utils/constants";
import type { PredictRequest } from "@/types/api";
import type { PlayerSummary } from "@/types/api";
import type { SelectOption } from "@/types/domain";

interface PredictionFormProps {
  players: PlayerSummary[];
  isSubmitting: boolean;
  onSubmit: (payload: PredictRequest) => void;
}

interface FormValues {
  player: string;
  team: string;
  opponent: string;
  venue: string;
  batting_position: string;
  innings_number: string;
  match_date: string;
}

const defaultValues: FormValues = {
  player: "",
  team: "",
  opponent: "",
  venue: "",
  batting_position: "",
  innings_number: "1",
  match_date: "",
};

export function PredictionForm({ players, isSubmitting, onSubmit }: PredictionFormProps) {
  const {
    control,
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<FormValues>({ defaultValues });

  const playerOptions: SelectOption[] = players.map((p) => ({ value: p.name, label: p.name }));
  const teamOptions: SelectOption[] = ASHES_TEAMS.map((t) => ({ value: t, label: t }));
  const venueOptions: SelectOption[] = ASHES_VENUES.map((v) => ({ value: v, label: v }));

  const selectedTeam = watch("team");
  const opponentOptions: SelectOption[] = ASHES_TEAMS.filter((t) => t !== selectedTeam).map(
    (t) => ({ value: t, label: t })
  );

  function submit(values: FormValues) {
    const payload: PredictRequest = {
      player: values.player,
      team: values.team,
      opponent: values.opponent,
      venue: values.venue,
      match_date: values.match_date,
      innings_number: Number(values.innings_number),
      batting_position: values.batting_position ? Number(values.batting_position) : null,
    };
    onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-5">
      <Controller
        name="player"
        control={control}
        rules={{ required: "Choose a player" }}
        render={({ field }) => (
          <SearchableSelect
            label="Player"
            options={playerOptions}
            value={field.value}
            onChange={field.onChange}
            placeholder="Search for a player..."
            error={errors.player?.message}
          />
        )}
      />

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Controller
          name="team"
          control={control}
          rules={{ required: "Choose a team" }}
          render={({ field }) => (
            <SearchableSelect
              label="Team"
              options={teamOptions}
              value={field.value}
              onChange={field.onChange}
              placeholder="Select team"
              error={errors.team?.message}
            />
          )}
        />
        <Controller
          name="opponent"
          control={control}
          rules={{ required: "Choose an opponent" }}
          render={({ field }) => (
            <SearchableSelect
              label="Opponent"
              options={opponentOptions}
              value={field.value}
              onChange={field.onChange}
              placeholder="Select opponent"
              error={errors.opponent?.message}
            />
          )}
        />
      </div>

      <Controller
        name="venue"
        control={control}
        rules={{ required: "Choose or enter a venue" }}
        render={({ field }) => (
          <SearchableSelect
            label="Venue"
            options={venueOptions}
            value={field.value}
            onChange={field.onChange}
            placeholder="Search for a venue..."
            allowFreeText
            error={errors.venue?.message}
          />
        )}
      />

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">
            Batting Position
          </label>
          <input
            type="number"
            min={1}
            max={11}
            placeholder="e.g. 4"
            className="w-full rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400"
            {...register("batting_position", { min: 1, max: 11 })}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">
            Innings Number
          </label>
          <select
            className="w-full rounded-xl border border-navy-100 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400"
            {...register("innings_number", { required: true })}
          >
            <option value="1">1st Innings</option>
            <option value="2">2nd Innings</option>
            <option value="3">3rd Innings</option>
            <option value="4">4th Innings</option>
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-navy-600">Match Date</label>
          <input
            type="date"
            className={`w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm outline-none focus:border-gold-400 ${
              errors.match_date ? "border-red-300" : "border-navy-100"
            }`}
            {...register("match_date", { required: "Pick a match date" })}
          />
          {errors.match_date && (
            <p className="mt-1.5 text-xs text-red-600">{errors.match_date.message}</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-3 pt-2">
        <Button type="submit" isLoading={isSubmitting} className="min-w-[160px]">
          <Search size={16} />
          Predict Runs
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => reset(defaultValues)}
          disabled={isSubmitting}
        >
          <Eraser size={16} />
          Clear
        </Button>
      </div>
    </form>
  );
}
