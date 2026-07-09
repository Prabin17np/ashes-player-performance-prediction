interface UrnMarkProps {
  className?: string;
  animated?: boolean;
}

/** The single illustrated signature element of the app: a pared-back
 * line drawing of the Ashes urn. Used large and quiet in the hero,
 * and small as a spinner glyph elsewhere -- never decorative filler. */
export function UrnMark({ className = "", animated = false }: UrnMarkProps) {
  return (
    <svg
      viewBox="0 0 120 160"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <g className={animated ? "origin-center animate-[spin_2.4s_linear_infinite]" : ""}>
        <path
          d="M60 8c-7 0-12 5-12 10v6c-14 3-22 12-22 24 0 4 2 7 5 9l4 24c1 8 8 14 16 14h18c8 0 15-6 16-14l4-24c3-2 5-5 5-9 0-12-8-21-22-24v-6c0-5-5-10-12-10Z"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />
        <path d="M44 24c4 2 8 3 16 3s12-1 16-3" stroke="currentColor" strokeWidth="2" />
        <path d="M38 95h44" stroke="currentColor" strokeWidth="2" />
        <path d="M45 128h30" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </g>
    </svg>
  );
}
