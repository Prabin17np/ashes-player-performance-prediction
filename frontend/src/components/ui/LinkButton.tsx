import { Link, LinkProps } from "react-router-dom";
import { buttonVariantClasses, buttonSizeClasses } from "./Button";

interface LinkButtonProps extends LinkProps {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function LinkButton({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...rest
}: LinkButtonProps) {
  return (
    <Link
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors duration-150 ${buttonVariantClasses[variant]} ${buttonSizeClasses[size]} ${className}`}
      {...rest}
    >
      {children}
    </Link>
  );
}
