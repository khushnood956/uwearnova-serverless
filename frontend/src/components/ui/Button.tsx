import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "accent" | "outline" | "ghost";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium tracking-wide transition-[background-color,color,border-color,box-shadow,transform] duration-base ease-out select-none disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]";

    const variantStyles = {
      primary:
        "bg-obsidian text-ivory hover:bg-champagne hover:text-obsidian border border-transparent shadow-subtle hover:shadow-card",
      secondary:
        "bg-ivory-sand text-obsidian hover:bg-ivory border border-obsidian/10",
      accent:
        "bg-champagne text-obsidian hover:bg-champagne-light border border-transparent font-semibold shadow-subtle",
      outline:
        "bg-transparent text-obsidian border border-obsidian/30 hover:bg-obsidian hover:text-ivory",
      ghost:
        "bg-transparent text-obsidian hover:text-champagne-dark border border-transparent",
    };

    const sizeStyles = {
      sm: "h-10 px-4 text-xs rounded-button gap-1.5",
      md: "h-12 px-6 text-sm rounded-button gap-2",
      lg: "h-14 px-8 text-base rounded-button gap-2.5",
      icon: "w-11 h-11 p-0 rounded-button aspect-square",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      >
        {isLoading ? (
          <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
