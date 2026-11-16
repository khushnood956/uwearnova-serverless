import { Breadcrumbs, BreadcrumbItem } from "@/components/common/Breadcrumbs";

export interface CollectionHeaderProps {
  title: string;
  description: string;
  itemCount: number;
  breadcrumbs: BreadcrumbItem[];
}

export function CollectionHeader({
  title,
  description,
  itemCount,
  breadcrumbs,
}: CollectionHeaderProps) {
  return (
    <div className="border-b border-hairline bg-ivory-sand py-10 sm:py-14 mb-8">
      <div className="container-site space-y-4">
        <Breadcrumbs items={breadcrumbs} />

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-3">
              <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-medium text-obsidian tracking-tight leading-tight">
                {title}
              </h1>
              <span className="px-3 py-1 rounded-button text-xs font-medium tracking-wide bg-ivory text-obsidian border border-hairline shadow-subtle">
                {itemCount} {itemCount === 1 ? "Piece" : "Pieces"}
              </span>
            </div>
            <p className="text-sm sm:text-base text-obsidian-600 leading-relaxed font-light">
              {description}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
