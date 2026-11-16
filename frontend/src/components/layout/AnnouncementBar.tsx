import { BRAND_CONFIG, formatPKR } from "@/lib/brand";

export function AnnouncementBar() {
  return (
    <div className="h-9 sm:h-10 bg-obsidian text-ivory-light flex items-center justify-center px-4 text-[11px] sm:text-xs font-medium tracking-wide uppercase select-none border-b border-obsidian-800">
      <span className="sm:hidden">
        Free shipping over {formatPKR(BRAND_CONFIG.freeShippingThreshold)} · COD available
      </span>
      <span className="hidden sm:inline">
        Free Nationwide Dispatch on Orders Over{" "}
        <strong className="text-champagne-light font-semibold">
          {formatPKR(BRAND_CONFIG.freeShippingThreshold)}
        </strong>{" "}
        · Cash on Delivery Nationwide
      </span>
    </div>
  );
}
