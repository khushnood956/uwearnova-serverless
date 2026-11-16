import { cache } from "react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProductBySlug as getStaticProductBySlug, PRODUCTS } from "@/data/products";
import { BRAND_CONFIG, formatPKR } from "@/lib/brand";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { SectionHeader } from "@/components/common/SectionHeader";
import { ProductGallery } from "@/components/product/ProductGallery";
import { VariantSelector } from "@/components/product/VariantSelector";
import { ProductAccordion } from "@/components/product/ProductAccordion";
import { ProductGrid } from "@/components/product/ProductGrid";
import { Badge } from "@/components/ui/Badge";
import { Star } from "lucide-react";
import { catalogApi } from "@/lib/api/catalog";
import { mapBackendProduct } from "@/lib/api/adapters";
import { Product } from "@/types/product";

interface ProductPageProps {
  params: Promise<{ slug: string }>;
}

/**
 * Deduplicated product resolver wrapped in React cache().
 * Shares a single network round-trip between generateMetadata and ProductDetailPage.
 */
const resolveProduct = cache(async (slug: string): Promise<Product | null> => {
  try {
    const backendProduct = await catalogApi.getProductBySlug(slug);
    if (backendProduct) {
      return mapBackendProduct(backendProduct);
    }
  } catch {
    // Backend product not found or offline, fallback to static
  }
  const staticProduct = getStaticProductBySlug(slug);
  return staticProduct || null;
});

export async function generateStaticParams() {
  if (PRODUCTS.length === 0) {
    return [{ slug: "_preview" }];
  }
  return PRODUCTS.map((product) => ({
    slug: product.slug,
  }));
}

export async function generateMetadata({
  params,
}: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await resolveProduct(slug);

  if (!product) {
    return {
      title: "Product Not Found",
    };
  }

  return {
    title: `${product.name} | ${BRAND_CONFIG.name}`,
    description: product.description,
    openGraph: {
      title: `${product.name} | ${BRAND_CONFIG.name}`,
      description: product.description,
      images: [
        {
          url: product.images[0],
          alt: product.name,
        },
      ],
    },
  };
}

export default async function ProductDetailPage({ params }: ProductPageProps) {
  const { slug } = await params;
  const product = await resolveProduct(slug);

  if (!product) {
    notFound();
  }

  // Related products in the same category
  let relatedProducts: Product[] = [];
  try {
    const res = await catalogApi.getProducts({ category_slug: product.category, limit: 5 });
    if (res && Array.isArray(res.items)) {
      relatedProducts = res.items
        .filter((p) => p.slug !== product.slug)
        .slice(0, 4)
        .map(mapBackendProduct);
    }
  } catch {
    // fallback
  }

  if (relatedProducts.length === 0) {
    relatedProducts = PRODUCTS.filter(
      (p) => p.category === product.category && p.slug !== product.slug
    ).slice(0, 4);
  }

  const discountPercent =
    product.originalPrice && product.originalPrice > product.price
      ? Math.round(
          ((product.originalPrice - product.price) / product.originalPrice) * 100
        )
      : null;

  return (
    <main className="flex-1 pb-16 bg-ivory">
      <div className="container-site pt-6 pb-12">
        <Breadcrumbs
          items={[
            { label: "Collections", href: "/collections/all" },
            {
              label: product.category,
              href: `/collections/${product.category}`,
            },
            { label: product.name },
          ]}
        />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-14 mt-6 items-start">
          {/* Left Column: Visual Gallery */}
          <div className="lg:col-span-7">
            <ProductGallery
              images={product.images}
              productName={product.name}
            />
          </div>

          {/* Right Column: Product Narrative & Configuration (Sticky on desktop) */}
          <div className="lg:col-span-5 space-y-6 lg:sticky lg:top-28">
            {/* Header / Titles */}
            <div className="space-y-2.5 border-b border-hairline pb-5">
              <div className="flex items-center gap-2">
                {product.isNewArrival && (
                  <Badge variant="accent" size="sm">
                    New Arrival
                  </Badge>
                )}
                {discountPercent !== null && (
                  <Badge variant="sale" size="sm">
                    Save {discountPercent}%
                  </Badge>
                )}
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-obsidian-500 capitalize">
                  {product.category}
                </span>
              </div>

              <h1 className="font-serif text-2xl sm:text-3xl lg:text-h2 font-medium text-obsidian tracking-tight leading-[1.1]">
                {product.name}
              </h1>

              {product.subtitle && (
                <p className="text-xs sm:text-sm font-medium tracking-[0.12em] uppercase text-champagne-dark">
                  {product.subtitle}
                </p>
              )}

              {/* Price & Rating */}
              <div className="pt-2 flex items-baseline justify-between">
                <div className="flex items-baseline gap-3">
                  <span className="font-serif text-2xl sm:text-3xl font-medium text-obsidian">
                    {formatPKR(product.price)}
                  </span>
                  {product.originalPrice && (
                    <span className="text-sm text-obsidian-400 line-through">
                      {formatPKR(product.originalPrice)}
                    </span>
                  )}
                </div>

                {product.rating && (
                  <div className="flex items-center gap-1.5 text-xs text-obsidian-700 bg-sand/40 px-2.5 py-1 rounded-button border border-hairline">
                    <Star className="w-3.5 h-3.5 fill-champagne text-champagne" />
                    <span className="font-semibold">{product.rating}</span>
                    <span className="text-obsidian-500">
                      ({product.reviewCount})
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Description */}
            <p className="text-sm text-obsidian-700 leading-relaxed font-light">
              {product.description}
            </p>

            {/* Variant Selector (Color, Size, Quantity, CTA) */}
            <VariantSelector product={product} />

            {/* Accordion Tabs */}
            <ProductAccordion
              items={[
                {
                  id: "fabric",
                  title: "Fabric & Craftsmanship",
                  iconType: "sparkles",
                  content: (
                    <div className="space-y-2">
                      <ul className="list-disc list-inside space-y-1">
                        {product.fabricCare ? (
                          product.fabricCare.map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))
                        ) : (
                          <>
                            <li>Custom woven luxury textile blend.</li>
                            <li>Dry clean recommended to preserve garment drape.</li>
                          </>
                        )}
                      </ul>
                    </div>
                  ),
                },
                {
                  id: "shipping",
                  title: "Nationwide Delivery & COD",
                  iconType: "truck",
                  content: (
                    <div className="space-y-1.5">
                      <p>
                        <strong>Standard Dispatch:</strong> 24–48 hours from our Sialkot fulfillment center.
                      </p>
                      <p>
                        <strong>Delivery Timeline:</strong> 2–4 business days across Karachi, Sialkot, Islamabad, and nationwide.
                      </p>
                      <p>
                        <strong>Payment:</strong> Cash on Delivery (COD) and major domestic cards supported soon.
                      </p>
                    </div>
                  ),
                },
                {
                  id: "exchanges",
                  title: "7-Day Complimentary Exchange",
                  iconType: "refresh",
                  content: (
                    <p>
                      Enjoy peace of mind with our 7-day door-to-door exchange policy. If the fit isn&apos;t flawless, our courier will swap your piece directly at your doorstep without return freight fees.
                    </p>
                  ),
                },
              ]}
            />
          </div>
        </div>

        {/* Related Products Section */}
        {relatedProducts.length > 0 && (
          <section className="mt-20 pt-12 border-t border-hairline">
            <SectionHeader
              eyebrow="Complete The Look"
              title="Complementary Pieces"
              linkText="Explore All"
              linkHref="/collections/all"
              className="mb-8"
            />
            <ProductGrid products={relatedProducts} columns={4} />
          </section>
        )}
      </div>
    </main>
  );
}
