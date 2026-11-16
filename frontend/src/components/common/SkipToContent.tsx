import Link from "next/link";

export function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-obsidian focus:text-white focus:rounded-button focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-champagne text-xs font-semibold uppercase tracking-wider"
    >
      Skip to Main Content
    </a>
  );
}
