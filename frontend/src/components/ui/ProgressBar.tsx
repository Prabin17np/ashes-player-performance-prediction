import { motion } from "framer-motion";

interface ProgressBarProps {
  label?: string;
}

/** An indeterminate progress bar: since the backend doesn't stream
 * partial progress, this simulates motion honestly (a sweeping
 * highlight, not a fake percentage) while a request is in flight. */
export function ProgressBar({ label }: ProgressBarProps) {
  return (
    <div className="w-full">
      {label && <p className="mb-2 text-sm text-slate-450">{label}</p>}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-navy-50">
        <motion.div
          className="h-full w-1/3 rounded-full bg-gradient-to-r from-gold-400 to-gold-600"
          animate={{ x: ["-100%", "220%"] }}
          transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    </div>
  );
}
