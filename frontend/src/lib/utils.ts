import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combines Tailwind class names cleanly without collision.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
