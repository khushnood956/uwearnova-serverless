import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Reveal } from "@/components/common/Reveal";

export function CampaignFeature() {
  return (
    <section className="relative w-full bg-obsidian text-ivory overflow-hidden border-y border-obsidian-800">
      <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[clamp(480px,65vh,640px)]">
        {/* Editorial Visual Column */}
        <div className="relative lg:col-span-7 min-h-[340px] lg:min-h-full overflow-hidden">
          <Image
            src="https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?q=85&w=1600&auto=format&fit=crop"
            alt="The Monolith Series Campaign Feature"
            fill
            sizes="(max-width: 1024px) 100vw, 60vw"
            className="object-cover object-[center_35%] transition-transform duration-slow ease-out hover:scale-105"
          />
          {/* Subtle gradient transition on desktop */}
          <div className="absolute inset-0 bg-gradient-to-t from-obsidian via-transparent to-transparent lg:bg-gradient-to-r lg:from-transparent lg:to-obsidian" />
        </div>

        {/* Narrative & Action Column */}
        <div className="relative lg:col-span-5 p-8 sm:p-12 lg:p-16 flex flex-col justify-center">
          <Reveal>
            <div className="space-y-6 max-w-lg">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-button bg-ivory-light/10 border border-ivory-light/15 text-xs font-semibold tracking-[0.18em] uppercase text-champagne-light">
                <Sparkles className="w-3 h-3 text-champagne" />
                <span>The Monolith Capsule</span>
              </div>

              <h2 className="font-serif text-h2 font-medium text-ivory tracking-tight leading-[1.12]">
                Architectural Form.{" "}
                <span className="italic font-normal text-champagne-light">
                  Effortless
                </span>{" "}
                Drape.
              </h2>

              <p className="text-sm sm:text-base text-ivory-light/80 leading-relaxed font-light">
                Rooted in quiet discipline, our limited-run Monolith capsule merges
                heavyweight virgin wools, subcontinental silk-linens, and sharp lapels
                engineered to command attention through understated nuance.
              </p>

              <div className="pt-2">
                <Link href="/collections/signature">
                  <Button
                    size="lg"
                    variant="accent"
                    className="bg-champagne text-obsidian hover:bg-champagne-light font-semibold shadow-card group/btn"
                  >
                    <span>Explore The Campaign</span>
                    <ArrowRight className="w-4 h-4 ml-2 transition-transform duration-base ease-out group-hover/btn:translate-x-1" />
                  </Button>
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
