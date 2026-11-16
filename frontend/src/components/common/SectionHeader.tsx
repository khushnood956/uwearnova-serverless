import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  linkText?: string;
  linkHref?: string;
  className?: string;
  align?: "left" | "center";
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  linkText,
  linkHref,
  className,
  align = "left",
}: SectionHeaderProps) {
  const isCenter = align === "center";

  return (
    <div
      className={cn(
        "mb-10 sm:mb-14",
        isCenter
          ? "text-center max-w-2xl mx-auto"
          : "flex flex-col sm:flex-row sm:items-end justify-between gap-4",
        className
      )}
    >
      <div className={cn("space-y-2", !isCenter && "max-w-xl")}>
        {eyebrow && (
          <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-champagne-dark">
            {eyebrow}
          </span>
        )}
        <h2 className="font-serif text-h2 font-medium text-obsidian tracking-tight leading-[1.12]">
          {title}
        </h2>
        {description && (
          <p className="text-sm sm:text-base text-obsidian-600 leading-relaxed font-light pt-1">
            {description}
          </p>
        )}
      </div>

      {linkText && linkHref && (
        <Link
          href={linkHref}
          className="group inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold tracking-wide uppercase text-obsidian hover:text-champagne-dark transition-colors duration-fast relative py-1 shrink-0"
        >
          <span>{linkText}</span>
          <ArrowRight className="w-4 h-4 transition-transform duration-base ease-out group-hover:translate-x-1" />
          <span className="absolute bottom-0 left-0 w-full h-[1px] bg-champagne-dark origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-base ease-out" />
        </Link>
      )}
    </div>
  );
}
