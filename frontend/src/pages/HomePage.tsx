import { Hero } from "@/components/home/Hero";
import { DashboardCards } from "@/components/home/DashboardCards";

export function HomePage() {
  return (
    <div>
      <Hero />
      <section className="mx-auto max-w-6xl px-6 pb-20">
        <DashboardCards />
      </section>
    </div>
  );
}
