"use client";

import * as React from "react";
import Link from "next/link";
import { AlertCircle, RotateCcw, Home, ShoppingBag } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error("Application encountered an unexpected error:", error);
  }, [error]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4 py-16">
      <div className="max-w-md w-full bg-ivory-light border border-hairline rounded-card p-8 sm:p-10 shadow-card text-center space-y-6">
        <div className="w-14 h-14 mx-auto rounded-full bg-crimson/10 border border-crimson/20 flex items-center justify-center text-crimson">
          <AlertCircle className="w-7 h-7" />
        </div>

        <div className="space-y-2">
          <h2 className="font-serif text-2xl sm:text-3xl font-medium text-obsidian tracking-tight">
            Something went wrong
          </h2>
          <p className="text-sm text-obsidian-600 leading-relaxed font-light">
            We encountered an unexpected issue while loading this page. Our team has been notified.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Button
            onClick={() => reset()}
            variant="primary"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Try Again
          </Button>
          <Link href="/" className="w-full sm:w-auto">
            <Button
              variant="secondary"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2"
            >
              <Home className="w-4 h-4" />
              Return Home
            </Button>
          </Link>
        </div>

        {process.env.NODE_ENV === "development" && error?.message && (
          <div className="mt-4 p-3 bg-obsidian-900 text-ivory-light rounded text-left text-xs font-mono overflow-auto max-h-32 border border-obsidian-800">
            <p className="font-bold text-amber-400">Dev Notice:</p>
            <p>{error.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}
