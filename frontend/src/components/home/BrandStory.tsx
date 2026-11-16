import { ShieldCheck, Truck, RefreshCw, Sparkles } from "lucide-react";
import { BRAND_CONFIG } from "@/lib/brand";
import { SectionHeader } from "@/components/common/SectionHeader";
import { Reveal } from "@/components/common/Reveal";

const PILLARS = [
  {
    icon: Sparkles,
    title: "Artisanal Tailoring",
    description:
      "Precision-tailored in limited ateliers using virgin wools and subcontinental hand-spun textiles chosen for longevity and drape.",
  },
  {
    icon: Truck,
    title: "Express Nationwide Dispatch",
    description:
      "Direct logistics from our Sialkot flagship atelier across Lahore, Karachi, Islamabad, and nationwide with swift 2–4 business day delivery.",
  },
  {
    icon: RefreshCw,
    title: "Doorstep Exchanges",
    description:
      "Complimentary 7-day door-to-door size and cut replacement for a frictionless, confident fitting experience.",
  },
  {
    icon: ShieldCheck,
    title: "Cash on Delivery",
    description:
      "Inspect your parcel at your doorstep with convenient cash on delivery available across all major Pakistani postal codes.",
  },
];

export function BrandStory() {
  return (
    <section className="section-spacing bg-ivory-sand border-b border-hairline">
      <div className="container-site">
        <Reveal>
          <SectionHeader
            align="center"
            eyebrow="Our Point of View"
            title="Modern Elegance Through Pure Form"
            description={`${BRAND_CONFIG.name} redefines contemporary luxury in Pakistan. We bridge minimalist silhouettes with tactile textiles, creating versatile staples engineered to feel exceptional from morning conferences to evening gatherings.`}
          />
        </Reveal>

        {/* Four Pillars with Hairline Dividers (No white box containers) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 pt-4 divide-y sm:divide-y-0 sm:divide-x divide-obsidian/10">
          {PILLARS.map((pillar, idx) => {
            const Icon = pillar.icon;
            return (
              <Reveal key={pillar.title} delay={idx * 60} className="pt-6 sm:pt-0 sm:px-6 first:pl-0 last:pr-0">
                <div className="space-y-3">
                  <div className="w-10 h-10 rounded-button bg-ivory flex items-center justify-center text-champagne-dark border border-hairline">
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-serif text-lg font-medium text-obsidian tracking-tight">
                    {pillar.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
                    {pillar.description}
                  </p>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
