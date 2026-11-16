import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", error, label, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-semibold uppercase tracking-[0.18em] text-obsidian-700"
          >
            {label}
          </label>
        )}
        <input
          id={inputId}
          type={type}
          ref={ref}
          className={cn(
            "w-full h-12 px-4 rounded-lg text-sm bg-ivory-light text-obsidian",
            "border border-obsidian/15 transition-colors duration-fast",
            "placeholder:text-obsidian-400 focus:outline-none focus:border-champagne-dark focus:ring-1 focus:ring-champagne-dark",
            "disabled:opacity-50 disabled:bg-ivory disabled:cursor-not-allowed",
            error && "border-sale focus:border-sale focus:ring-sale",
            className
          )}
          {...props}
        />
        {error && (
          <p className="text-xs text-sale mt-1 font-medium">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
