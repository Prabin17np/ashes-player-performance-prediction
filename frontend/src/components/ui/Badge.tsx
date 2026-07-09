import { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  tone?: "gold" | "navy" | "green" | "gray";
  className?: string;
}

const toneClasses: Record<string, string> = {
  gold: "bg-gold-50 text-gold-700 border-gold-200",
  navy: "bg-navy-50 text-navy-600 border-navy-100",
  green: "bg-emerald-50 text-emerald-700 border-emerald-200",
  gray: "bg-paper text-slate-450 border-navy-100",
};

export function Badge({ children, tone = "navy", className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${toneClasses[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
