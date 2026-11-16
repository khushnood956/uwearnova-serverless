"use client";

import * as React from "react";
import { ChevronDown, Sparkles, Truck, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface AccordionItem {
  id: string;
  title: string;
  iconType?: "sparkles" | "truck" | "refresh";
  content: React.ReactNode;
}

interface ProductAccordionProps {
  items: AccordionItem[];
}

export function ProductAccordion({ items }: ProductAccordionProps) {
  const [openIds, setOpenIds] = React.useState<string[]>([items[0]?.id || ""]);

  const toggle = (id: string) => {
    setOpenIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const renderIcon = (type?: "sparkles" | "truck" | "refresh") => {
    switch (type) {
      case "sparkles":
        return <Sparkles className="w-4 h-4 text-champagne-dark group-hover:text-obsidian transition-colors duration-fast" />;
      case "truck":
        return <Truck className="w-4 h-4 text-champagne-dark group-hover:text-obsidian transition-colors duration-fast" />;
      case "refresh":
        return <RefreshCw className="w-4 h-4 text-champagne-dark group-hover:text-obsidian transition-colors duration-fast" />;
      default:
        return null;
    }
  };

  return (
    <div className="divide-y divide-hairline border-y border-hairline">
      {items.map((item) => {
        const isOpen = openIds.includes(item.id);

        return (
          <div key={item.id} className="py-4">
            <button
              type="button"
              onClick={() => toggle(item.id)}
              aria-expanded={isOpen}
              className="flex w-full items-center justify-between text-left group cursor-pointer"
            >
              <div className="flex items-center gap-2.5">
                {renderIcon(item.iconType)}
                <span className="text-sm font-serif font-medium text-obsidian group-hover:text-champagne-dark transition-colors duration-fast">
                  {item.title}
                </span>
              </div>
              <ChevronDown
                className={cn(
                  "w-4 h-4 text-obsidian-500 transition-transform duration-base ease-out",
                  isOpen && "transform rotate-180"
                )}
              />
            </button>

            {isOpen && (
              <div className="pt-3 pb-1 text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
                {item.content}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
