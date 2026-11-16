import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "accent" | "outline" | "sale" | "success";
  size?: "sm" | "md";
}

export function Badge({
  className,
  variant = "default",
  size = "md",
  ...props
}: BadgeProps) {
  const baseStyles =
    "inline-flex items-center font-medium tracking-wider uppercase transition-colors duration-fast";

  const variantStyles = {
    default: "bg-ivory-sand text-obsidian border border-obsidian/10",
    accent: "bg-champagne/15 text-champagne-dark border border-champagne/30",
    outline: "border border-obsidian/25 text-obsidian bg-transparent",
    sale: "bg-sale/10 text-sale border border-sale/25 font-semibold",
    success: "bg-success/10 text-success border border-success/25 font-medium",
  };

  const sizeStyles = {
    sm: "text-[10px] px-2 py-0.5 rounded-button tracking-wider",
    md: "text-xs px-2.5 py-1 rounded-button",
  };

  return (
    <span
      className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
      {...props}
    />
  );
}
