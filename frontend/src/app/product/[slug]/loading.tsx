import * as React from "react";

/**
 * Product Detail Loading Skeleton
 * Transitions instantaneously on product link navigation, eliminating perception of delay.
 */
export default function ProductLoading() {
  return (
    <main className="flex-1 pb-16 bg-ivory animate-pulse">
      <div className="container-site pt-6 pb-12">
        {/* Breadcrumb Skeleton */}
        <div className="flex items-center space-x-2 mb-6">
          <div className="h-3 w-16 bg-sand/60 rounded" />
          <span className="text-obsidian-300 text-xs">/</span>
          <div className="h-3 w-20 bg-sand/60 rounded" />
          <span className="text-obsidian-300 text-xs">/</span>
          <div className="h-3 w-32 bg-sand/80 rounded" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-14 items-start">
          {/* Left Column: Visual Gallery Skeleton */}
          <div className="lg:col-span-7 space-y-4">
            <div className="aspect-[3/4] w-full bg-sand/50 rounded-xl" />
            <div className="flex gap-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="w-20 h-24 bg-sand/40 rounded-lg shrink-0" />
              ))}
            </div>
          </div>

          {/* Right Column: Configuration & Narrative Skeleton */}
          <div className="lg:col-span-5 space-y-6">
            {/* Badges & Titles */}
            <div className="space-y-3 border-b border-hairline pb-5">
              <div className="flex items-center gap-2">
                <div className="h-5 w-20 bg-champagne-light/60 rounded-full" />
                <div className="h-3 w-16 bg-sand/40 rounded" />
              </div>
              <div className="h-8 sm:h-10 w-4/5 bg-sand/80 rounded" />
              <div className="h-4 w-1/3 bg-sand/50 rounded" />
              <div className="flex items-baseline justify-between pt-2">
                <div className="h-8 w-28 bg-sand/90 rounded" />
                <div className="h-6 w-16 bg-sand/40 rounded-button" />
              </div>
            </div>

            {/* Description Paragraph */}
            <div className="space-y-2">
              <div className="h-3 w-full bg-sand/50 rounded" />
              <div className="h-3 w-5/6 bg-sand/50 rounded" />
              <div className="h-3 w-2/3 bg-sand/40 rounded" />
            </div>

            {/* Variant Options Skeleton */}
            <div className="space-y-4 pt-2">
              <div className="space-y-2">
                <div className="h-3 w-16 bg-sand/60 rounded" />
                <div className="flex gap-2">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-9 w-12 bg-sand/50 rounded-button" />
                  ))}
                </div>
              </div>

              {/* CTA Button Skeleton */}
              <div className="h-12 w-full bg-obsidian/20 rounded-button mt-4" />
            </div>

            {/* Accordion Skeletons */}
            <div className="space-y-2 pt-4 border-t border-hairline">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-11 w-full bg-sand/30 rounded-lg" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
