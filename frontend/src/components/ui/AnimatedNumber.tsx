import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
  durationMs?: number;
}

/** Counts up from 0 to `value` once it scrolls into view, rendered in
 * tabular mono digits with a thin gold rule beneath -- the scoreboard
 * motif used throughout the app for every stat and prediction. */
export function AnimatedNumber({
  value,
  decimals = 0,
  suffix = "",
  className = "",
  durationMs = 900,
}: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const start = performance.now();
    let frame: number;

    function tick(now: number) {
      const progress = Math.min((now - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(value * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    }

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [inView, value, durationMs]);

  return (
    <span ref={ref} className="inline-block">
      <span className={`font-mono ${className}`}>
        {display.toFixed(decimals)}
        {suffix}
      </span>
      <motion.span
        initial={{ scaleX: 0 }}
        animate={{ scaleX: inView ? 1 : 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
        className="block h-[2px] origin-left bg-gold-500 mt-1"
      />
    </span>
  );
}
