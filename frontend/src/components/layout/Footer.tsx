import { UrnMark } from "@/components/ui/UrnMark";

export function Footer() {
  return (
    <footer className="border-t border-navy-50 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="seam-divider mb-8 w-full opacity-40" />
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2.5">
            <UrnMark className="h-6 w-6 text-gold-600" />
            <div>
              <p className="font-display text-sm font-semibold text-navy-700">
                Ashes Cricket Player Performance Prediction System
              </p>
              <p className="text-xs text-slate-450">Final Year Project</p>
            </div>
          </div>
          <div className="text-xs text-slate-450 sm:text-right">
            <p>
              Developed by <span className="font-medium text-navy-600">Prabin</span>
            </p>
            <p>2026</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
