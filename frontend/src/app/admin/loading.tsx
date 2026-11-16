import * as React from "react";

/**
 * Admin Console Loading Skeleton
 * Instant visual feedback when navigating between administrative workspace tabs.
 */
export default function AdminLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header Skeleton */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div className="space-y-2">
          <div className="h-4 w-28 bg-sand/60 rounded" />
          <div className="h-8 w-64 bg-sand/80 rounded" />
        </div>
        <div className="h-9 w-32 bg-sand/50 rounded-button" />
      </div>

      {/* Metric Cards Skeleton */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="p-5 rounded-xl bg-ivory-light border border-hairline space-y-3">
            <div className="flex items-center justify-between">
              <div className="h-3 w-20 bg-sand/50 rounded" />
              <div className="h-7 w-7 rounded-lg bg-sand/40" />
            </div>
            <div className="h-7 w-28 bg-sand/80 rounded" />
          </div>
        ))}
      </div>

      {/* Table / Content Skeleton */}
      <div className="bg-ivory-light border border-hairline rounded-xl p-6 space-y-4">
        <div className="h-5 w-40 bg-sand/70 rounded" />
        <div className="space-y-3 pt-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 w-full bg-sand/30 rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}
