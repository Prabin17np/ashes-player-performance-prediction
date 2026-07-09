import { Cpu, Database, GitBranch, Server } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { UrnMark } from "@/components/ui/UrnMark";

const stack = [
  { icon: <Server size={18} />, label: "FastAPI backend serving /health, /players, /predict, /simulate" },
  { icon: <Cpu size={18} />, label: "Random Forest regression model trained on historical Test innings" },
  { icon: <Database size={18} />, label: "Historical Ashes batting data used for feature engineering" },
  { icon: <GitBranch size={18} />, label: "React, TypeScript, and Vite frontend consuming the API" },
];

export function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <div className="mb-10 flex items-center gap-4">
        <UrnMark className="h-10 w-10 text-gold-600" />
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-gold-600">
            About the project
          </p>
          <h1 className="font-display text-3xl font-semibold text-navy-700">
            Ashes Cricket Player Performance Prediction
          </h1>
        </div>
      </div>

      <p className="text-sm leading-relaxed text-slate-450">
        This system predicts Test cricket batting performance for the Ashes rivalry between
        England and Australia. Given a player, matchup, venue, and innings context, the
        underlying model estimates the runs that player is likely to score — either for a single
        innings or across an entire simulated series.
      </p>

      <p className="mt-4 text-sm leading-relaxed text-slate-450">
        It was built as a Final Year Project to explore how historical statistical patterns in
        Test cricket can be modelled and served through a production-style API, with this
        interface acting as the demonstration layer for a university dissertation presentation.
      </p>

      <div className="mt-10 space-y-3">
        {stack.map((item, i) => (
          <Card key={i} delay={i * 0.05} className="flex items-center gap-3.5 p-4">
            <span className="text-gold-500">{item.icon}</span>
            <p className="text-sm text-navy-600">{item.label}</p>
          </Card>
        ))}
      </div>

      <div className="mt-10 seam-divider w-full opacity-40" />
      <p className="mt-6 text-xs text-slate-450">
        Developed by Prabin · Final Year Project, 2026
      </p>
    </div>
  );
}
