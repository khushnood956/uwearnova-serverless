import Link from "next/link";
import Image from "next/image";
import { ArrowUpRight } from "lucide-react";
import { CATEGORIES } from "@/data/categories";
import { SectionHeader } from "@/components/common/SectionHeader";
import { Reveal } from "@/components/common/Reveal";

const CATEGORY_COUNTS: Record<string, string> = {
  women: "42 Pieces",
  men: "38 Pieces",
  kids: "26 Pieces",
  footwear: "Coming Soon",
  accessories: "Coming Soon",
};

export function CategoryGrid() {
  return (
    <section className="section-spacing bg-ivory border-b border-hairline">
      <div className="container-site">
        <Reveal>
          <SectionHeader
            eyebrow="Curated Lines"
            title="Shop by Category"
            description="Deliberate capsules defined by tactile textiles, sculptural tailoring, and effortless subcontinental living."
            linkText="View All Collections"
            linkHref="/collections/all"
          />
        </Reveal>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {CATEGORIES.map((cat, idx) => (
            <Reveal key={cat.slug} delay={idx * 60}>
              <Link
                href={`/collections/${cat.slug}`}
                className="group relative flex flex-col rounded-card overflow-hidden bg-ivory-light border border-hairline shadow-subtle hover:shadow-card-hover hover:-translate-y-1 transition-[transform,box-shadow] duration-base ease-out select-none"
              >
                {/* 3:4 Aspect Ratio Container */}
                <div className="relative aspect-[3/4] w-full overflow-hidden bg-ivory-sand">
                  <Image
                    src={cat.image}
                    alt={cat.name}
                    fill
                    sizes="(max-width: 640px) 50vw, (max-width: 1024px) 50vw, 25vw"
                    className="object-cover object-center transition-transform duration-slow ease-out group-hover:scale-105"
                  />
                  {/* Subtle bottom gradient localized to text */}
                  <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-obsidian/85 via-obsidian/30 to-transparent pointer-events-none" />

                  {/* Piece count pill */}
                  <span className="absolute top-3 right-3 px-2.5 py-1 rounded-button text-[10px] font-semibold tracking-wider uppercase bg-ivory-light/90 text-obsidian backdrop-blur-xs shadow-subtle">
                    {CATEGORY_COUNTS[cat.slug] || "In Stock"}
                  </span>

                  {/* Bottom Text Content */}
                  <div className="absolute bottom-3 left-3 right-3 sm:bottom-4 sm:left-4 sm:right-4 text-ivory">
                    <div className="flex items-center justify-between">
                      <h3 className="font-serif text-lg sm:text-xl font-medium tracking-tight leading-snug">
                        {cat.name}
                      </h3>
                      <div className="w-8 h-8 rounded-button bg-ivory-light/20 backdrop-blur-xs flex items-center justify-center text-ivory group-hover:bg-champagne group-hover:text-obsidian transition-colors duration-fast shrink-0">
                        <ArrowUpRight className="w-4 h-4" />
                      </div>
                    </div>
                    <p className="text-xs text-ivory-light/75 line-clamp-1 font-light mt-0.5">
                      {cat.description}
                    </p>
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
