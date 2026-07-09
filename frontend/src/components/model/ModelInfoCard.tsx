import { Cpu, Database, Target } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { useModelInfo } from "@/hooks/useModelInfo";

export function ModelInfoCard() {
  const { data, loading, error } = useModelInfo();

  if (loading) {
    return (
      <Card className="p-6">
        <p className="text-sm text-slate-450">Loading model info…</p>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="p-6">
        <p className="text-sm text-red-500">{error ?? "Model info unavailable"}</p>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-semibold text-navy-700">
          {data.model_name}
        </h3>
        <Badge tone="gold">{data.algorithm}</Badge>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-450">
            <Database size={16} className="text-gold-500" />
            Training Samples
          </div>
          <p className="mt-1 font-mono text-xl font-semibold text-navy-700">
            <AnimatedNumber value={data.training_samples} decimals={0} />
          </p>
        </div>

        <div>
          <div className="flex items-center gap-2 text-sm text-slate-450">
            <Cpu size={16} className="text-gold-500" />
            Features
          </div>
          <p className="mt-1 font-mono text-xl font-semibold text-navy-700">
            <AnimatedNumber value={data.features} decimals={0} />
          </p>
        </div>

        <div>
          <div className="flex items-center gap-2 text-sm text-slate-450">
            <Target size={16} className="text-gold-500" />
            Test MAE
          </div>
          <p className="mt-1 font-mono text-xl font-semibold text-navy-700">
            <AnimatedNumber value={data.test_mae} decimals={2} />
          </p>
        </div>

        <div>
          <div className="flex items-center gap-2 text-sm text-slate-450">
            <Target size={16} className="text-gold-500" />
            Test R²
          </div>
          <p className="mt-1 font-mono text-xl font-semibold text-navy-700">
            <AnimatedNumber value={data.test_r2} decimals={3} />
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4 border-t border-navy-50 pt-4 text-sm text-slate-450">
        <span>CV MAE: <span className="font-mono text-navy-600">{data.cv_mae.toFixed(2)}</span></span>
        <span>CV RMSE: <span className="font-mono text-navy-600">{data.cv_rmse.toFixed(2)}</span></span>
        <span>CV R²: <span className="font-mono text-navy-600">{data.cv_r2.toFixed(3)}</span></span>
      </div>
    </Card>
  );
}