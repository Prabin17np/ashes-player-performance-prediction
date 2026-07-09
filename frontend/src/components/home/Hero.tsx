import { motion } from "framer-motion";
import { LinkButton } from "@/components/ui/LinkButton";
import { UrnMark } from "@/components/ui/UrnMark";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-navy-50/60 via-transparent to-transparent" />
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:py-28">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <p className="mb-4 text-xs font-medium uppercase tracking-[0.2em] text-gold-600">
            Final Year Project · Test Cricket Analytics
          </p>
          <h1 className="font-display text-4xl font-semibold leading-[1.08] text-navy-700 sm:text-5xl lg:text-6xl">
            Ashes Cricket Player
            <br />
            Performance Prediction
          </h1>
          <p className="mt-6 max-w-lg text-base leading-relaxed text-slate-450">
            Predict batting performance using historical Test cricket data and
            machine learning — from a single innings to an entire series.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <LinkButton size="lg" to="/predict">
              Predict Player
            </LinkButton>
            <LinkButton size="lg" variant="secondary" to="/simulate">
              Simulate Series
            </LinkButton>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
          className="relative flex justify-center"
        >
          <div className="relative flex h-72 w-72 items-center justify-center rounded-full bg-white shadow-card lg:h-80 lg:w-80">
            <div className="absolute inset-4 rounded-full border border-gold-200" />
            <UrnMark className="h-36 w-36 text-navy-600" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}
