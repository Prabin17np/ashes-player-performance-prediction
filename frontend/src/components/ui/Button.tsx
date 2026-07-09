import { ButtonHTMLAttributes, forwardRef, useState, MouseEvent } from "react";
import { motion } from "framer-motion";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const buttonVariantClasses: Record<string, string> = {
  primary:
    "bg-navy-700 text-white hover:bg-navy-600 focus-visible:outline-gold-500 disabled:bg-navy-300",
  secondary:
    "bg-white text-navy-700 border border-navy-100 hover:border-gold-400 hover:text-navy-800 disabled:opacity-50",
  ghost: "bg-transparent text-navy-500 hover:bg-navy-50 disabled:opacity-50",
  danger: "bg-white text-red-600 border border-red-200 hover:bg-red-50",
};

export const buttonSizeClasses: Record<string, string> = {
  sm: "text-sm px-3 py-1.5",
  md: "text-sm px-4 py-2.5",
  lg: "text-base px-6 py-3",
};

const variantClasses = buttonVariantClasses;
const sizeClasses = buttonSizeClasses;

interface Ripple {
  x: number;
  y: number;
  id: number;
}

/** A button with a restrained ripple: one soft radial pulse from the
 * click point, not a full material-style splash -- keeps the "avoid
 * overusing animation" brief while still giving tactile feedback. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", isLoading, className = "", children, onClick, disabled, ...rest }, ref) => {
    const [ripples, setRipples] = useState<Ripple[]>([]);

    function handleClick(e: MouseEvent<HTMLButtonElement>) {
      const rect = e.currentTarget.getBoundingClientRect();
      const id = Date.now();
      setRipples((r) => [...r, { x: e.clientX - rect.left, y: e.clientY - rect.top, id }]);
      setTimeout(() => setRipples((r) => r.filter((rp) => rp.id !== id)), 500);
      onClick?.(e);
    }

    return (
      <button
        ref={ref}
        className={`relative overflow-hidden isolate inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors duration-150 disabled:cursor-not-allowed ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
        onClick={handleClick}
        disabled={disabled || isLoading}
        {...rest}
      >
        {ripples.map((r) => (
          <motion.span
            key={r.id}
            className="absolute rounded-full bg-white/30 pointer-events-none"
            style={{ left: r.x, top: r.y, translateX: "-50%", translateY: "-50%" }}
            initial={{ width: 0, height: 0, opacity: 0.6 }}
            animate={{ width: 220, height: 220, opacity: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        ))}
        {isLoading && (
          <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
        )}
        <span className="relative z-10">{children}</span>
      </button>
    );
  }
);
Button.displayName = "Button";
