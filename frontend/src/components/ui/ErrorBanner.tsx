import { AlertTriangle } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3.5 text-sm text-red-700 animate-fade-in">
      <AlertTriangle size={18} className="mt-0.5 flex-shrink-0" />
      <div className="flex-1">
        <p>{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-1.5 font-medium underline underline-offset-2 hover:text-red-800"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
