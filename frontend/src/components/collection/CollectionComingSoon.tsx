import Link from "next/link";
import { Sparkles, ArrowRight } from "lucide-react";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";

interface CollectionComingSoonProps {
  title: string;
  departmentSlug: string;
}

export function CollectionComingSoon({ title, departmentSlug }: CollectionComingSoonProps) {
  return (
    <main className="flex-1 pb-20">
      {/* Header with Breadcrumbs */}
      <div className="border-b border-hairline bg-ivory-sand py-8 mb-12">
        <div className="container-site">
          <Breadcrumbs
            items={[
              { label: "Home", href: "/" },
              { label: "Collections", href: "/collections/all" },
              { label: title },
            ]}
          />
        </div>
      </div>

      <div className="container-site max-w-2xl text-center py-12 px-4 sm:px-6">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-champagne-light text-champagne-dark border border-champagne-dark/20 text-xs font-semibold uppercase tracking-widest mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Curated Anticipation</span>
        </div>

        <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-medium text-obsidian tracking-tight mb-4">
          {title}
        </h1>

        <p className="font-serif text-xl sm:text-2xl text-champagne-dark italic mb-6">
          &ldquo;More to explore. New collections are coming soon.&rdquo;
        </p>

        <p className="text-sm sm:text-base text-obsidian-600 leading-relaxed max-w-lg mx-auto mb-10 font-light">
          Our atelier is carefully crafting the premier {title.toLowerCase()} collection.
          Every piece is designed with understated discipline and exquisite material integrity.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <Link
            href="/collections/men"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-button bg-obsidian text-ivory text-xs uppercase tracking-wider font-semibold hover:bg-obsidian-800 transition-colors"
          >
            <span>Explore Men&apos;s Wardrobe</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/collections/women"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 rounded-button bg-ivory text-obsidian border border-obsidian/20 text-xs uppercase tracking-wider font-semibold hover:bg-ivory-sand transition-colors"
          >
            <span>Explore Women&apos;s Wardrobe</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
