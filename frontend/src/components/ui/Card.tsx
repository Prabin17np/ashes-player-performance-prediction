import { ReactNode } from "react";
import { motion } from "framer-motion";

interface CardProps {
  hoverElevate?: boolean;
  delay?: number;
  className?: string;
  children?: ReactNode;
}

export function Card({ hoverElevate, delay = 0, className = "", children }: CardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
      whileHover={hoverElevate ? { y: -3 } : undefined}
      className={`rounded-2xl bg-white shadow-card ${
        hoverElevate ? "transition-shadow hover:shadow-card-hover" : ""
      } ${className}`}
    >
      {children}
    </motion.div>
  );
}
