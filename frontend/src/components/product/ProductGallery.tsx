"use client";

import * as React from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface ProductGalleryProps {
  images: string[];
  productName: string;
}

export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [activeIndex, setActiveIndex] = React.useState(0);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const activeImage = images[activeIndex] || images[0];

  const handleMobileScroll = () => {
    if (!scrollRef.current) return;
    const scrollLeft = scrollRef.current.scrollLeft;
    const width = scrollRef.current.offsetWidth;
    const index = Math.round(scrollLeft / width);
    if (index >= 0 && index < images.length && index !== activeIndex) {
      setActiveIndex(index);
    }
  };

  const scrollToImage = (idx: number) => {
    setActiveIndex(idx);
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        left: idx * scrollRef.current.offsetWidth,
        behavior: "smooth",
      });
    }
  };

  return (
    <div className="flex flex-col-reverse lg:flex-row gap-4">
      {/* Thumbnail Strip (Desktop) */}
      {images.length > 1 && (
        <div className="hidden lg:flex flex-col gap-3 overflow-y-auto max-h-[640px] shrink-0">
          {images.map((img, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => scrollToImage(idx)}
              className={cn(
                "relative w-20 h-24 rounded-image overflow-hidden border-2 bg-ivory shrink-0 transition-[border-color,opacity] duration-fast ease-out",
                activeIndex === idx
                  ? "border-obsidian opacity-100"
                  : "border-transparent opacity-60 hover:opacity-100"
              )}
              aria-label={`View angle ${idx + 1} of ${productName}`}
            >
              <Image
                src={img}
                alt={`${productName} thumbnail ${idx + 1}`}
                fill
                sizes="80px"
                className="object-cover object-center"
              />
            </button>
          ))}
        </div>
      )}

      {/* Main Image Container */}
      <div className="relative w-full">
        {/* Desktop Single Display */}
        <div className="hidden lg:block relative aspect-[4/5] w-full rounded-image overflow-hidden bg-sand/30 border border-hairline shadow-subtle">
          <Image
            src={activeImage}
            alt={`${productName} angle ${activeIndex + 1}`}
            fill
            priority
            sizes="(max-width: 1024px) 100vw, 50vw"
            className="object-cover object-center transition-transform duration-slow ease-out hover:scale-[1.02]"
          />
        </div>

        {/* Mobile Horizontal Snap Carousel */}
        <div
          ref={scrollRef}
          onScroll={handleMobileScroll}
          className="lg:hidden flex overflow-x-auto snap-x snap-mandatory scrollbar-none w-full aspect-[4/5] rounded-image border border-hairline bg-sand/30"
          style={{ scrollSnapType: "x mandatory", WebkitOverflowScrolling: "touch" }}
        >
          {images.map((img, idx) => (
            <div
              key={idx}
              className="relative w-full h-full shrink-0 snap-start snap-always"
            >
              <Image
                src={img}
                alt={`${productName} view ${idx + 1}`}
                fill
                priority={idx === 0}
                sizes="100vw"
                className="object-cover object-center"
              />
            </div>
          ))}
        </div>

        {/* Mobile Indicator Dots */}
        {images.length > 1 && (
          <div className="flex lg:hidden items-center justify-center gap-1.5 mt-3">
            {images.map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => scrollToImage(idx)}
                aria-label={`Go to image ${idx + 1}`}
                className={cn(
                  "h-1.5 rounded-full transition-[width,background-color] duration-fast ease-out",
                  activeIndex === idx ? "w-6 bg-obsidian" : "w-1.5 bg-obsidian/30"
                )}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
