import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { CollectionHeader } from "@/components/collection/CollectionHeader";
import { CollectionBrowser } from "@/components/collection/CollectionBrowser";
import { CollectionComingSoon } from "@/components/collection/CollectionComingSoon";
import { PRODUCTS } from "@/data/products";
import { BRAND_CONFIG } from "@/lib/brand";
import { Product } from "@/types/product";
import { catalogApi } from "@/lib/api/catalog";
import { mapBackendProduct } from "@/lib/api/adapters";

interface PageProps {
  params: Promise<{ category: string }>;
}

const COMING_SOON_DEPARTMENTS: Record<string, string> = {
  footwear: "Footwear",
  accessories: "Accessories",
  perfumes: "Perfumes",
};

interface CollectionMeta {
  title: string;
  description: string;
  filter?: (product: Product) => boolean;
}

const STATIC_COLLECTIONS: Record<string, CollectionMeta> = {
  all: {
    title: "Complete Catalogue",
    description:
      "Explore the complete UWEARNOVA wardrobe — contemporary apparel, artisanal footwear, and leather accessories.",
  },
  men: {
    title: "Men's Wardrobe",
    description:
      "Structured blazers, relaxed linen shirts, and architectural pleated trousers crafted for the modern gentleman.",
    filter: (p) => p.category === "men",
  },
  women: {
    title: "Women's Collection",
    description:
      "Fluid silhouettes, sculpted midi dresses, and fine cashmere knits combining minimal discipline with effortless grace.",
    filter: (p) => p.category === "women",
  },
  kids: {
    title: "Kids' Collection",
    description:
      "Comfortable, premium essentials tailored for everyday movement and play.",
    filter: (p) => (p.category as string) === "kids",
  },
  "new-arrivals": {
    title: "New Arrivals",
    description:
      "The latest seasonal designs, newly released textiles, and recent additions to our luxury lineup.",
    filter: (p) => Boolean(p.isNewArrival),
  },
  essentials: {
    title: "Everyday Essentials",
    description:
      "Foundational wardrobe cornerstones designed to be worn on repeat with lasting texture and integrity.",
  },
  signature: {
    title: "Signature Collection",
    description:
      "Our most prestigious artisanal cuts, featuring virgin wool blends, Japanese crepe, and bespoke finishing.",
  },
  trending: {
    title: "Trending Pieces",
    description:
      "The most coveted styles and seasonal favorites across Pakistan this month.",
    filter: (p) => Boolean(p.isTrending),
  },
  sale: {
    title: "Seasonal Offers",
    description:
      "Special seasonal reductions on select archival styles and limited pieces.",
    filter: (p) => Boolean(p.originalPrice && p.originalPrice > p.price),
  },
};

export async function generateStaticParams() {
  const staticSlugs = [
    "all",
    "men",
    "women",
    "kids",
    "footwear",
    "accessories",
    "perfumes",
    "new-arrivals",
    "essentials",
    "signature",
    "trending",
    "sale",
  ];
  return staticSlugs.map((category) => ({ category }));
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { category } = await params;
  const slug = category.toLowerCase();

  if (COMING_SOON_DEPARTMENTS[slug]) {
    return {
      title: `${COMING_SOON_DEPARTMENTS[slug]} — Coming Soon | ${BRAND_CONFIG.name}`,
      description: "More to explore. New collections are coming soon.",
    };
  }

  const meta = STATIC_COLLECTIONS[slug];
  const title = meta ? meta.title : slug.charAt(0).toUpperCase() + slug.slice(1).replace(/-/g, " ");

  return {
    title: `${title} | ${BRAND_CONFIG.name}`,
    description: meta?.description || `Explore our latest ${title} collection.`,
  };
}

export default async function CollectionPage({ params }: PageProps) {
  const { category } = await params;
  const slug = category.toLowerCase();

  // 1. Check if known coming-soon department
  if (COMING_SOON_DEPARTMENTS[slug]) {
    return (
      <CollectionComingSoon
        title={COMING_SOON_DEPARTMENTS[slug]}
        departmentSlug={slug}
      />
    );
  }

  // 2. Fetch live data from backend concurrently (eliminating sequential waterfalls)
  let liveProducts: Product[] = [];
  let categoryTitle = STATIC_COLLECTIONS[slug]?.title;
  let categoryDesc = STATIC_COLLECTIONS[slug]?.description;

  try {
    const queryParams: Record<string, any> = { limit: 50 };
    if (slug !== "all") {
      queryParams.category_slug = slug;
    }

    // Parallelize category info and products queries across the wire to Supabase
    const [catResult, productsResult] = await Promise.allSettled([
      catalogApi.getCategory(slug),
      catalogApi.getProducts(queryParams),
    ]);

    if (catResult.status === "fulfilled" && catResult.value) {
      const cat = catResult.value;
      categoryTitle = cat.name;
      if (cat.description) categoryDesc = cat.description;
      if (cat.is_coming_soon) {
        return (
          <CollectionComingSoon
            title={cat.name || slug}
            departmentSlug={slug}
          />
        );
      }
    }

    if (productsResult.status === "fulfilled" && productsResult.value?.items) {
      liveProducts = productsResult.value.items.map(mapBackendProduct);
    }
  } catch (err) {
    console.warn(`Could not load backend products for ${slug}:`, err);
  }

  // Fallback to static products if backend produced no products
  if (liveProducts.length === 0) {
    const staticMeta = STATIC_COLLECTIONS[slug];
    if (staticMeta?.filter) {
      liveProducts = PRODUCTS.filter(staticMeta.filter);
    } else if (slug === "all") {
      liveProducts = PRODUCTS;
    }
  }

  const displayTitle =
    categoryTitle ||
    slug
      .split("-")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

  const displayDesc =
    categoryDesc ||
    `Explore curated pieces designed with modern precision and timeless elegance.`;

  return (
    <main className="flex-1 pb-16">
      <CollectionHeader
        title={displayTitle}
        description={displayDesc}
        itemCount={liveProducts.length}
        breadcrumbs={[
          { label: "Collections", href: "/collections/all" },
          { label: displayTitle },
        ]}
      />

      <div className="container-site mt-8">
        <CollectionBrowser initialProducts={liveProducts} categorySlug={slug} />
      </div>
    </main>
  );
}
