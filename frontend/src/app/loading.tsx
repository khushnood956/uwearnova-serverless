import * as React from "react";

/**
 * Root Loading State
 * Instant visual feedback during top-level App Router transitions.
 */
export default function RootLoading() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] bg-ivory">
      {/* Top indeterminate luxury progress hairline */}
      <div className="fixed top-0 left-0 right-0 h-[2px] bg-ivory-sand overflow-hidden z-50">
        <div className="h-full bg-champagne-dark animate-pulse w-1/3 mx-auto" />
      </div>

      <div className="flex flex-col items-center space-y-4">
        {/* Luxury circular spinner */}
        <div className="relative w-10 h-10">
          <div className="w-10 h-10 rounded-full border-2 border-hairline" />
          <div className="absolute top-0 left-0 w-10 h-10 rounded-full border-2 border-champagne-dark border-t-transparent animate-spin" />
        </div>
        <p className="text-[11px] font-semibold tracking-[0.2em] uppercase text-obsidian-400">
          UWEARNOVA
        </p>
      </div>
    </div>
  );
}
