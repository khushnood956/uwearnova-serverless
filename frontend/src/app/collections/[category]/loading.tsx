import * as React from "react";

/**
 * Collection Page Loading Skeleton
 * Renders instantaneously on collection route navigations, eliminating perception of delay.
 */
export default function CollectionLoading() {
  return (
    <main className="flex-1 pb-16 bg-ivory animate-pulse">
      {/* Header Skeleton */}
      <div className="bg-ivory-sand/40 border-b border-hairline py-8 sm:py-12">
        <div className="container-site space-y-4">
          {/* Breadcrumb Skeleton */}
          <div className="flex items-center space-x-2">
            <div className="h-3 w-16 bg-sand/60 rounded" />
            <span className="text-obsidian-300 text-xs">/</span>
            <div className="h-3 w-24 bg-sand/80 rounded" />
          </div>

          {/* Title & Count Skeleton */}
          <div className="flex items-baseline gap-3">
            <div className="h-8 sm:h-10 w-64 bg-sand/80 rounded" />
            <div className="h-4 w-12 bg-sand/50 rounded-full" />
          </div>

          {/* Description Skeleton */}
          <div className="h-4 w-full max-w-xl bg-sand/50 rounded" />
        </div>
      </div>

      {/* Grid Area Skeleton */}
      <div className="container-site mt-8 space-y-6">
        {/* Filter Bar Skeleton */}
        <div className="flex items-center justify-between pb-4 border-b border-hairline">
          <div className="flex items-center gap-2">
            <div className="h-8 w-20 bg-sand/50 rounded-button" />
            <div className="h-8 w-24 bg-sand/50 rounded-button hidden sm:block" />
          </div>
          <div className="h-8 w-32 bg-sand/50 rounded-button" />
        </div>

        {/* 4-Column Product Grid Skeletons */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-8">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="flex flex-col space-y-3">
              {/* Product Card Image Skeleton */}
              <div className="aspect-[3/4] w-full bg-sand/50 rounded-lg overflow-hidden relative">
                <div className="absolute top-2 left-2 h-4 w-12 bg-ivory/60 rounded-full" />
              </div>
              {/* Details Skeletons */}
              <div className="space-y-1.5 pt-1">
                <div className="h-3 w-16 bg-sand/40 rounded" />
                <div className="h-4 w-3/4 bg-sand/70 rounded" />
                <div className="h-4 w-1/3 bg-sand/80 rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
