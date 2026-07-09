interface CricketBatIconProps {
  size?: number;
  className?: string;
}

export function CricketBatIcon({ size = 18, className = "" }: CricketBatIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M17.5 3.5c1.2 1.2 1.2 3.1 0 4.3L10 15.3l-2.6-2.6L14.9 5c1.2-1.2 3.1-1.2 4.3 0Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M7.4 12.7 4 16.1c-.6.6-.6 1.6 0 2.2l1.7 1.7c.6.6 1.6.6 2.2 0l3.4-3.4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}
