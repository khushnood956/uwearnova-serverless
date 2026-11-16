import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb" className="py-3">
      <ol className="flex items-center space-x-2 text-xs text-obsidian-500">
        <li>
          <Link
            href="/"
            className="hover:text-obsidian transition-colors flex items-center gap-1"
          >
            <Home className="w-3.5 h-3.5" />
            <span className="sr-only">Home</span>
          </Link>
        </li>
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={item.label} className="flex items-center space-x-2">
              <ChevronRight className="w-3 h-3 text-obsidian-400" />
              {item.href && !isLast ? (
                <Link
                  href={item.href}
                  className="hover:text-obsidian transition-colors capitalize"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  className="font-medium text-obsidian capitalize"
                  aria-current={isLast ? "page" : undefined}
                >
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
