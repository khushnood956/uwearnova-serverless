"use client";

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  className,
}: ModalProps) {
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-obsidian/60 backdrop-blur-xs transition-opacity duration-200"
      />

      {/* Modal Dialog Card */}
      <div
        className={cn(
          "relative w-full max-w-lg bg-ivory-light rounded-card shadow-card-hover border border-obsidian/10 p-6 sm:p-8 z-10 transition-[opacity,transform] duration-base ease-out",
          className
        )}
      >
        <button
          onClick={onClose}
          aria-label="Close dialog"
          className="absolute top-4 right-4 p-2 text-obsidian-400 hover:text-obsidian rounded-full hover:bg-ivory transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {title && (
          <h2
            id="modal-title"
            className="text-xl font-serif font-semibold text-obsidian tracking-tight"
          >
            {title}
          </h2>
        )}

        {description && (
          <p className="mt-1 text-sm text-obsidian-600 leading-relaxed">
            {description}
          </p>
        )}

        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}
