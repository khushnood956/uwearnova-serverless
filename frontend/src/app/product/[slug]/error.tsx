"use client";

import * as React from "react";
import Link from "next/link";
import { AlertCircle, RotateCcw, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function ProductError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  React.useEffect(() => {
    console.error("Product page error:", error);
  }, [error]);

  return (
    <div className="container-site py-20 px-4 text-center">
      <div className="max-w-lg mx-auto bg-ivory-light border border-hairline rounded-card p-8 sm:p-12 shadow-subtle space-y-6">
        <div className="w-12 h-12 mx-auto rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600">
          <AlertCircle className="w-6 h-6" />
        </div>

        <div className="space-y-2">
          <h1 className="font-serif text-2xl sm:text-3xl font-medium text-obsidian tracking-tight">
            Product Not Found
          </h1>
          <p className="text-sm text-obsidian-600 leading-relaxed font-light">
            This piece may have been archived or is temporarily unavailable in our catalog.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link href="/collections/all">
            <Button
              variant="primary"
              className="inline-flex items-center justify-center gap-2"
            >
              Explore Full Collection
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
          <Link href="/">
            <Button
              variant="secondary"
              className="inline-flex items-center justify-center gap-2"
            >
              Return Home
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
