import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Search, X } from "lucide-react";
import type { SelectOption } from "@/types/domain";

interface SearchableSelectProps {
  label: string;
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  allowFreeText?: boolean;
  disabled?: boolean;
}

/** A combobox: type to filter, click to pick. Falls back to accepting
 * free text (`allowFreeText`) for fields like Venue or Opponent where
 * the historical dataset may not cover every future fixture. */
export function SearchableSelect({
  label,
  options,
  value,
  onChange,
  placeholder = "Search...",
  error,
  allowFreeText = false,
  disabled,
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, query]);

  const selectedLabel = options.find((o) => o.value === value)?.label ?? value;

  return (
    <div className="w-full" ref={containerRef}>
      <label className="mb-1.5 block text-sm font-medium text-navy-600">{label}</label>
      <div className="relative">
        <button
          type="button"
          disabled={disabled}
          onClick={() => setOpen((o) => !o)}
          className={`flex w-full items-center justify-between rounded-xl border bg-white px-3.5 py-2.5 text-left text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? "border-red-300" : "border-navy-100 hover:border-gold-300"
          }`}
        >
          <span className={value ? "text-navy-700" : "text-slate-450"}>
            {value ? selectedLabel : placeholder}
          </span>
          <ChevronDown size={16} className="text-slate-450" />
        </button>

        {value && !disabled && (
          <button
            type="button"
            aria-label={`Clear ${label}`}
            onClick={(e) => {
              e.stopPropagation();
              onChange("");
              setQuery("");
            }}
            className="absolute right-8 top-1/2 -translate-y-1/2 text-slate-450 hover:text-navy-600"
          >
            <X size={14} />
          </button>
        )}

        {open && !disabled && (
          <div className="absolute z-20 mt-1.5 w-full overflow-hidden rounded-xl border border-navy-100 bg-white shadow-card-hover">
            <div className="flex items-center gap-2 border-b border-navy-50 px-3 py-2">
              <Search size={14} className="text-slate-450" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={`Search ${label.toLowerCase()}...`}
                className="w-full text-sm outline-none placeholder:text-slate-450"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && allowFreeText && query.trim()) {
                    onChange(query.trim());
                    setOpen(false);
                  }
                }}
              />
            </div>
            <ul className="max-h-56 overflow-y-auto py-1">
              {filtered.length === 0 && (
                <li className="px-3.5 py-2.5 text-sm text-slate-450">
                  {allowFreeText ? "No matches — press Enter to use this value" : "No matches found"}
                </li>
              )}
              {filtered.map((o) => (
                <li key={o.value}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(o.value);
                      setQuery("");
                      setOpen(false);
                    }}
                    className={`flex w-full items-center justify-between px-3.5 py-2.5 text-left text-sm hover:bg-paper ${
                      o.value === value ? "bg-gold-50 text-navy-700" : "text-navy-600"
                    }`}
                  >
                    {o.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {error && <p className="mt-1.5 text-xs text-red-600">{error}</p>}
    </div>
  );
}
