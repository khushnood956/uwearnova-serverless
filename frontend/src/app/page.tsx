import { Hero } from "@/components/home/Hero";
import { CategoryGrid } from "@/components/home/CategoryGrid";
import { CampaignFeature } from "@/components/home/CampaignFeature";
import { FeaturedCollections } from "@/components/home/FeaturedCollections";
import { BrandStory } from "@/components/home/BrandStory";
import { ProductGrid } from "@/components/product/ProductGrid";
import { SectionHeader } from "@/components/common/SectionHeader";
import { Reveal } from "@/components/common/Reveal";
import { getTrendingProducts } from "@/data/products";

export default function HomePage() {
  const trendingProducts = getTrendingProducts().slice(0, 4);

  return (
    <main className="flex-1 flex flex-col">
      <Hero />
      <CategoryGrid />

      {/* Trending Pieces on Sand Background */}
      {trendingProducts.length > 0 && (
        <section className="section-spacing bg-ivory-sand border-b border-hairline">
          <div className="container-site">
            <Reveal>
              <SectionHeader
                eyebrow="Season Essentials"
                title="Trending Pieces"
                description="Coveted seasonal tailoring, fluid separates, and handcrafted footwear."
                linkText="View Full Catalogue"
                linkHref="/collections/all"
              />
            </Reveal>

            <Reveal delay={120}>
              {/* Grid 4 columns: 2 on mobile, 4 on desktop (NO 3+1 orphan bug) */}
              <ProductGrid products={trendingProducts} columns={4} />
            </Reveal>
          </div>
        </section>
      )}

      <CampaignFeature />
      <FeaturedCollections />
      <BrandStory />
    </main>
  );
}
