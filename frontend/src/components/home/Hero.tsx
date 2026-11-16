"use client";

import * as React from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ChevronLeft, ChevronRight, Sparkles, ShieldCheck, Truck, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { BRAND_CONFIG, formatPKR } from "@/lib/brand";

interface HeroSlide {
  id: string;
  eyebrow: string;
  titlePrimary: string;
  titleItalic: string;
  titleSecondary: string;
  description: string;
  imageUrl: string;
  imageAlt: string;
  objectPosition: string;
  primaryCtaText: string;
  primaryCtaHref: string;
  secondaryCtaText: string;
  secondaryCtaHref: string;
}

const HERO_SLIDES: HeroSlide[] = [
  {
    id: "capsule-aw",
    eyebrow: "Autumn / Winter Capsule",
    titlePrimary: "A New",
    titleItalic: "Dimension",
    titleSecondary: "of Style.",
    description:
      "Architectural cuts, refined subcontinental tailoring, and tactile virgin textiles created for contemporary Pakistani sensibilities.",
    imageUrl:
      "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?q=85&w=2400&auto=format&fit=crop",
    imageAlt: "UWEARNOVA Autumn Winter High Fashion Editorial Campaign",
    objectPosition: "object-[60%_30%] sm:object-[65%_center]",
    primaryCtaText: "Explore Collection",
    primaryCtaHref: "/collections/all",
    secondaryCtaText: "New Arrivals",
    secondaryCtaHref: "/collections/new-arrivals",
  },
  {
    id: "outerwear-monolith",
    eyebrow: "Signature Outerwear",
    titlePrimary: "Structured",
    titleItalic: "Modernity",
    titleSecondary: "in Form.",
    description:
      "Heavyweight virgin wool blazers, overshirts, and sculptural silhouettes balancing architectural rigor with subcontinental ease.",
    imageUrl:
      "https://images.unsplash.com/photo-1509631179647-0177331693ae?q=85&w=2400&auto=format&fit=crop",
    imageAlt: "UWEARNOVA Monolith Outerwear Tailoring Editorial",
    objectPosition: "object-[55%_25%] sm:object-[60%_center]",
    primaryCtaText: "Men's Collection",
    primaryCtaHref: "/collections/men",
    secondaryCtaText: "Signature Capsule",
    secondaryCtaHref: "/collections/signature",
  },
  {
    id: "silk-twill",
    eyebrow: "Artisan Craft & Silk Twill",
    titlePrimary: "Sensory",
    titleItalic: "Elegance",
    titleSecondary: "& Drape.",
    description:
      "Hand-finished Egyptian cotton shirting, mulberry silk twills, and extra-fine Mongolian cashmere knitwear crafted to endure.",
    imageUrl:
      "https://images.unsplash.com/photo-1469334031218-e382a71b716b?q=85&w=2400&auto=format&fit=crop",
    imageAlt: "UWEARNOVA Silk Twill and Natural Luxury Textiles",
    objectPosition: "object-[70%_25%] sm:object-[65%_center]",
    primaryCtaText: "Women's Collection",
    primaryCtaHref: "/collections/women",
    secondaryCtaText: "The Essentials",
    secondaryCtaHref: "/collections/essentials",
  },
];

export function Hero() {
  const [currentSlide, setCurrentSlide] = React.useState(0);
  const [isPaused, setIsPaused] = React.useState(false);

  const totalSlides = HERO_SLIDES.length;

  // Auto-advance slides every 6.5 seconds when not hovered
  React.useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % totalSlides);
    }, 6500);
    return () => clearInterval(interval);
  }, [isPaused, totalSlides]);

  const goToSlide = (idx: number) => {
    setCurrentSlide(idx);
  };

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % totalSlides);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + totalSlides) % totalSlides);
  };

  const active = HERO_SLIDES[currentSlide];

  return (
    <section
      className="group relative isolate overflow-hidden w-full h-[clamp(580px,88svh,840px)] flex flex-col justify-between bg-obsidian text-ivory select-none"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      aria-label="Editorial Hero Campaign Carousel"
    >
      {/* Background Editorial Image Layers with Smooth Cross-Fade */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        {HERO_SLIDES.map((slide, idx) => {
          const isActive = idx === currentSlide;
          return (
            <div
              key={slide.id}
              className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${
                isActive ? "opacity-100 z-10" : "opacity-0 z-0 pointer-events-none"
              }`}
            >
              <Image
                src={slide.imageUrl}
                alt={slide.imageAlt}
                fill
                priority={idx === 0}
                sizes="100vw"
                className={`object-cover ${slide.objectPosition} transition-transform duration-[6500ms] ease-out ${
                  isActive ? "scale-105" : "scale-100"
                }`}
              />
              {/* Obsidian Vignette Gradient Overlay */}
              <div className="absolute inset-0 bg-gradient-to-r from-obsidian/90 via-obsidian/55 to-transparent sm:via-obsidian/35" />
              <div className="absolute bottom-0 inset-x-0 h-1/3 bg-gradient-to-t from-obsidian/90 to-transparent pointer-events-none" />
            </div>
          );
        })}
      </div>

      {/* Main Content Vertically Centered */}
      <div className="flex-1 flex items-center relative z-20">
        <div className="container-site w-full py-12">
          <div className="max-w-2xl space-y-6">
            {/* Eyebrow badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-button bg-ivory-light/15 backdrop-blur-md border border-ivory-light/20 text-xs font-semibold tracking-[0.18em] uppercase text-champagne-light animate-fade-in">
              <Sparkles className="w-3.5 h-3.5 text-champagne" />
              <span>{active.eyebrow}</span>
            </div>

            {/* Display Heading with Italic Word */}
            <h1 className="font-serif text-display font-medium text-ivory-light leading-[1.06] tracking-tight transition-all duration-500">
              {active.titlePrimary}{" "}
              <span className="italic font-normal text-champagne-light">
                {active.titleItalic}
              </span>{" "}
              {active.titleSecondary}
            </h1>

            {/* Supporting Copy */}
            <p className="text-base sm:text-lg text-ivory-light/85 max-w-lg leading-relaxed font-light transition-all duration-500">
              {active.description}
            </p>

            {/* Action Buttons */}
            <div className="pt-2 flex flex-col sm:flex-row gap-4 sm:items-center">
              <Link href={active.primaryCtaHref} className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="accent"
                  className="w-full sm:w-auto bg-champagne text-obsidian hover:bg-champagne-light font-semibold shadow-card group/btn"
                >
                  <span>{active.primaryCtaText}</span>
                  <ArrowRight className="w-4 h-4 ml-2 transition-transform duration-base ease-out group-hover/btn:translate-x-1" />
                </Button>
              </Link>

              <Link href={active.secondaryCtaHref} className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto text-ivory border-ivory/30 hover:border-ivory hover:bg-ivory hover:text-obsidian"
                >
                  {active.secondaryCtaText}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Slide Controls & Carousel Indicators (Desktop & Mobile) */}
      <div className="relative z-20 pb-4">
        <div className="container-site flex items-center justify-between">
          {/* Pill Indicators */}
          <div className="flex items-center gap-2.5">
            {HERO_SLIDES.map((slide, idx) => {
              const isActive = idx === currentSlide;
              return (
                <button
                  key={slide.id}
                  onClick={() => goToSlide(idx)}
                  className={`h-1.5 transition-all duration-500 rounded-full ${
                    isActive
                      ? "w-10 bg-champagne shadow-[0_0_8px_rgba(209,178,124,0.6)]"
                      : "w-3 bg-ivory/30 hover:bg-ivory/60"
                  }`}
                  aria-label={`Go to slide ${idx + 1}: ${slide.eyebrow}`}
                />
              );
            })}
            <span className="ml-3 text-xs tracking-widest text-champagne-light/80 font-mono">
              0{currentSlide + 1} / 0{totalSlides}
            </span>
          </div>

          {/* Navigation Arrows */}
          <div className="flex items-center gap-2">
            <button
              onClick={prevSlide}
              aria-label="Previous editorial slide"
              className="p-2 rounded-full border border-ivory/20 text-ivory/80 hover:text-champagne-light hover:border-champagne hover:bg-obsidian/60 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={nextSlide}
              aria-label="Next editorial slide"
              className="p-2 rounded-full border border-ivory/20 text-ivory/80 hover:text-champagne-light hover:border-champagne hover:bg-obsidian/60 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Trust & Delivery Strip */}
      <div className="relative z-20 border-t border-ivory-light/10 bg-obsidian/60 backdrop-blur-md py-3 text-xs text-ivory-light/75">
        <div className="container-site flex flex-wrap items-center justify-between gap-3 font-light tracking-wide">
          <div className="flex items-center gap-2">
            <Truck className="w-3.5 h-3.5 text-champagne-light" />
            <span>Free nationwide dispatch over {formatPKR(BRAND_CONFIG.freeShippingThreshold)}</span>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-champagne-light" />
            <span>Cash on Delivery across Pakistan</span>
          </div>
          <div className="flex items-center gap-2">
            <RefreshCw className="w-3.5 h-3.5 text-champagne-light" />
            <span>7-day doorstep exchanges</span>
          </div>
        </div>
      </div>
    </section>
  );
}