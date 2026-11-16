import Link from "next/link";
import Image from "next/image";
import { ArrowRight } from "lucide-react";
import { SectionHeader } from "@/components/common/SectionHeader";
import { Reveal } from "@/components/common/Reveal";

interface CollectionCard {
  tag: string;
  title: string;
  description: string;
  href: string;
  image: string;
}

const COLLECTIONS: CollectionCard[] = [
  {
    tag: "Just Released",
    title: "New Arrivals",
    description: "Transitional tailoring with clean proportions and tactile draping.",
    href: "/collections/new-arrivals",
    image:
      "https://images.unsplash.com/photo-1496747611176-843222e1e57c?q=85&w=1000&auto=format&fit=crop",
  },
  {
    tag: "Core Wardrobe",
    title: "Everyday Essentials",
    description: "Supima cottons, relaxed trousers, and enduring foundational staples.",
    href: "/collections/essentials",
    image:
      "https://images.unsplash.com/photo-1516762689617-e1cffcef479d?q=85&w=1000&auto=format&fit=crop",
  },
  {
    tag: "Limited Run",
    title: "Signature Collection",
    description: "Exclusive ceremonial eveningwear and hand-finished outerwear statements.",
    href: "/collections/signature",
    image:
      "https://images.unsplash.com/photo-1509631179647-0177331693ae?q=85&w=1000&auto=format&fit=crop",
  },
];

export function FeaturedCollections() {
  return (
    <section className="section-spacing bg-ivory border-b border-hairline">
      <div className="container-site">
        <Reveal>
          <SectionHeader
            eyebrow="Curated Capsules"
            title="Featured Collections"
            description="Focused sartorial themes engineered for seasonal versatility."
            linkText="View All Collections"
            linkHref="/collections/all"
          />
        </Reveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {COLLECTIONS.map((item, idx) => (
            <Reveal key={item.href} delay={idx * 80}>
              <Link
                href={item.href}
                className="group relative flex flex-col justify-end aspect-[3/4] sm:aspect-[4/5] rounded-card overflow-hidden bg-ivory-sand border border-hairline shadow-subtle hover:shadow-card-hover hover:-translate-y-1 transition-[transform,box-shadow] duration-base ease-out select-none"
              >
                {/* Background Image */}
                <Image
                  src={item.image}
                  alt={item.title}
                  fill
                  sizes="(max-width: 768px) 100vw, 33vw"
                  className="object-cover object-center transition-transform duration-slow ease-out group-hover:scale-105"
                />

                {/* Subtle bottom gradient only behind text */}
                <div className="absolute inset-0 bg-gradient-to-t from-obsidian/90 via-obsidian/40 to-transparent pointer-events-none" />

                {/* Top Tag */}
                <div className="absolute top-4 left-4 z-10">
                  <span className="px-3 py-1 rounded-button text-[10px] font-semibold uppercase tracking-[0.18em] bg-ivory-light/90 text-obsidian backdrop-blur-xs shadow-subtle">
                    {item.tag}
                  </span>
                </div>

                {/* Text Content Directly Over Image (No white boxes) */}
                <div className="relative z-10 p-6 space-y-2 text-ivory">
                  <h3 className="font-serif text-xl sm:text-2xl font-medium tracking-tight group-hover:text-champagne-light transition-colors duration-fast">
                    {item.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-ivory-light/80 leading-relaxed font-light line-clamp-2">
                    {item.description}
                  </p>

                  <div className="pt-2 flex items-center text-xs font-semibold tracking-wider uppercase text-champagne-light group-hover:text-white transition-colors duration-fast">
                    <span>Explore Capsule</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1.5 transition-transform duration-base ease-out group-hover:translate-x-1" />
                  </div>
                </div>
              </Link>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
