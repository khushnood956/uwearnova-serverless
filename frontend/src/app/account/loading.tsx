import * as React from "react";

/**
 * Customer Sanctuary Loading Skeleton
 * Instant visual feedback when navigating to /account.
 */
export default function AccountLoading() {
  return (
    <main className="flex-1 pb-20 bg-ivory animate-pulse">
      <div className="container-site pt-6 pb-12">
        <div className="h-4 w-24 bg-sand/60 rounded mb-4" />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline mt-4">
          <div className="space-y-2">
            <div className="h-3 w-28 bg-sand/50 rounded" />
            <div className="h-8 w-64 bg-sand/80 rounded" />
            <div className="h-4 w-96 bg-sand/40 rounded" />
          </div>
          <div className="h-9 w-24 bg-sand/40 rounded-button" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-8 items-start">
          <div className="lg:col-span-3 bg-ivory-light rounded-xl border border-hairline p-3 space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-9 w-full bg-sand/40 rounded-lg" />
            ))}
          </div>

          <div className="lg:col-span-9 bg-ivory-light rounded-2xl border border-hairline p-6 sm:p-8 space-y-6">
            <div className="h-6 w-48 bg-sand/70 rounded" />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="p-4 rounded-xl bg-ivory border border-hairline h-20" />
              ))}
            </div>
            <div className="space-y-3 pt-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-16 w-full bg-sand/30 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
