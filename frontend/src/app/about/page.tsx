import Image from "next/image";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { SectionHeader } from "@/components/common/SectionHeader";
import { BRAND_CONFIG } from "@/lib/brand";

export const metadata = {
  title: "About Our Atelier | UWEARNOVA",
  description: "The design philosophy, textile heritage, and modern vision of UWEARNOVA.",
};

export default function AboutPage() {
  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-4">
        <Breadcrumbs items={[{ label: "About Us" }]} />
      </div>

      {/* Editorial Header */}
      <section className="container-site py-8 lg:py-12">
        <div className="max-w-3xl">
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Our Heritage & Philosophy
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-display font-medium text-obsidian tracking-tight leading-[1.08] mt-3">
            Modern Elegance. Pakistan&apos;s New Aesthetic Standard.
          </h1>
          <p className="text-base sm:text-lg text-obsidian-600 mt-5 font-light leading-relaxed">
            {BRAND_CONFIG.name} was founded on a singular conviction: luxury does not require excessive adornment. True distinction lives in architectural proportion, superior cloth, and mindful tailoring.
          </p>
        </div>
      </section>

      {/* Full-width Editorial Visual Banner */}
      <section className="w-full relative h-[360px] sm:h-[480px] lg:h-[560px] overflow-hidden bg-obsidian">
        <Image
          src="https://images.unsplash.com/photo-1441986300917-64674bd600d8?q=80&w=1600&auto=format&fit=crop"
          alt="The UWEARNOVA fashion atelier workshop"
          fill
          priority
          sizes="100vw"
          className="object-cover object-center opacity-85"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-obsidian/60 via-transparent to-transparent" />
        <div className="absolute bottom-8 left-0 right-0 container-site text-ivory">
          <p className="text-xs uppercase tracking-[0.2em] font-medium text-champagne-light">
            Lahore Atelier &bull; Est. 2024
          </p>
        </div>
      </section>

      {/* 4 Stat Row */}
      <section className="bg-sand/60 border-y border-hairline py-10">
        <div className="container-site grid grid-cols-2 lg:grid-cols-4 gap-8 text-center">
          <div>
            <span className="font-serif text-3xl sm:text-4xl font-medium text-obsidian block">
              100%
            </span>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-obsidian-600 mt-1 block">
              Traceable Textiles
            </span>
          </div>
          <div>
            <span className="font-serif text-3xl sm:text-4xl font-medium text-obsidian block">
              40+
            </span>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-obsidian-600 mt-1 block">
              Master Artisans
            </span>
          </div>
          <div>
            <span className="font-serif text-3xl sm:text-4xl font-medium text-obsidian block">
              7-Day
            </span>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-obsidian-600 mt-1 block">
              Doorstep Exchange
            </span>
          </div>
          <div>
            <span className="font-serif text-3xl sm:text-4xl font-medium text-obsidian block">
              Zero
            </span>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-obsidian-600 mt-1 block">
              Fast-Fashion Synthetics
            </span>
          </div>
        </div>
      </section>

      {/* Editorial Content with Drop Cap and Split Visual */}
      <section className="container-site py-16 lg:py-24">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          <div className="lg:col-span-7 space-y-6 text-sm sm:text-base text-obsidian-700 leading-relaxed font-light">
            <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark block">
              The Philosophy of Form
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl lg:text-h2 font-medium text-obsidian tracking-tight leading-tight">
              Quiet Luxury Designed for Daily Elevation
            </h2>
            <p className="first-letter:float-left first-letter:text-5xl first-letter:pr-3 first-letter:font-serif first-letter:font-medium first-letter:text-obsidian first-letter:leading-none">
              Operating between our design studio in Lahore and artisanal workshops across Pakistan, we craft garments defined by discipline and freedom. Each season begins with yarn selection: virgin wools from ethical spinners, breathable Egyptian Giza cottons, and lustrous mulberry silks.
            </p>
            <p>
              We eliminate fleeting fast-fashion trends in favor of timeless capsules. By focusing on restrained palettes—obsidian, warm ivory, champagne, and stone—our pieces effortlessly integrate into your existing wardrobe, designed to transcend seasons and outlast trends.
            </p>
          </div>

          <div className="lg:col-span-5 relative aspect-[3/4] rounded-image overflow-hidden border border-hairline bg-sand/30 shadow-subtle">
            <Image
              src="https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=900&auto=format&fit=crop"
              alt="Artisanal tailoring in progress"
              fill
              sizes="(max-width: 1024px) 100vw, 450px"
              className="object-cover object-center"
            />
          </div>
        </div>
      </section>

      {/* Large Italic Serif Pull Quote */}
      <section className="bg-obsidian text-ivory py-16 sm:py-20 border-y border-obsidian-800">
        <div className="container-site text-center max-w-4xl mx-auto px-4">
          <p className="font-serif italic text-2xl sm:text-3xl lg:text-4xl text-ivory-light leading-relaxed font-normal">
            &ldquo;True distinction lives in architectural proportion, superior cloth, and the unspoken confidence of restraint.&rdquo;
          </p>
          <span className="mt-6 block text-xs tracking-[0.22em] uppercase text-champagne font-semibold">
            UWEARNOVA Design Direction &bull; Lahore
          </span>
        </div>
      </section>
    </main>
  );
}
