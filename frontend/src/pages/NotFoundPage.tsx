import { LinkButton } from "@/components/ui/LinkButton";
import { UrnMark } from "@/components/ui/UrnMark";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-6 py-24 text-center">
      <UrnMark className="h-16 w-16 text-navy-200" />
      <h1 className="mt-6 font-display text-3xl font-semibold text-navy-700">
        This innings wasn't played
      </h1>
      <p className="mt-2 text-sm text-slate-450">
        The page you're looking for doesn't exist. Let's get you back to the pitch.
      </p>
      <LinkButton to="/" className="mt-8">
        Back to Home
      </LinkButton>
    </div>
  );
}
