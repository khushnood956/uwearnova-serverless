import Link from "next/link";
import { ArrowRight, Compass } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <main className="min-h-[70vh] flex items-center justify-center px-4 py-20 text-center">
      <div className="max-w-md w-full space-y-6">
        <div className="w-16 h-16 mx-auto rounded-full bg-champagne/10 border border-champagne/20 flex items-center justify-center text-champagne-dark">
          <Compass className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <span className="text-xs uppercase tracking-[0.2em] text-obsidian-400 font-medium">
            404 — Page Not Found
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl font-medium text-obsidian tracking-tight">
            Lost in the Wardrobe
          </h1>
          <p className="text-sm text-obsidian-600 leading-relaxed font-light">
            The page or piece you are searching for does not exist or may have been relocated.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link href="/collections/all">
            <Button
              variant="primary"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto"
            >
              Explore Catalogue
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <Link href="/">
            <Button
              variant="secondary"
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto"
            >
              Return Home
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
