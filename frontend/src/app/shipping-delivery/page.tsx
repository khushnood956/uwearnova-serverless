import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { Truck, Clock, ShieldCheck, MapPin } from "lucide-react";
import { BRAND_CONFIG, formatPKR } from "@/lib/brand";

export const metadata = {
  title: "Shipping & Nationwide Delivery | UWEARNOVA",
  description: "Nationwide dispatch timelines, delivery fees, and cash on delivery procedures across Pakistan.",
};

export default function ShippingPage() {
  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-4">
        <Breadcrumbs items={[{ label: "Shipping & Delivery" }]} />
      </div>

      <div className="container-site max-w-4xl py-6 space-y-12">
        {/* Header */}
        <div className="border-b border-hairline pb-8">
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Nationwide Logistics
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-h2 font-medium text-obsidian tracking-tight mt-2">
            Shipping & Doorstep Delivery
          </h1>
          <p className="text-sm sm:text-base text-obsidian-600 mt-3 font-light leading-relaxed">
            Swift, white-glove fulfillment delivering luxury garments directly to your doorstep across all major cities and postal districts in Pakistan.
          </p>
        </div>

        {/* 3 Pillar Feature Cards on Sand */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-card bg-sand/40 border border-hairline space-y-3">
            <div className="w-10 h-10 rounded-full bg-ivory-light border border-hairline flex items-center justify-center text-champagne-dark">
              <Clock className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-obsidian">24–48h Dispatch</h3>
            <p className="text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
              Orders are packaged in archival tissue and dispatched from our Sialkot flagship atelier within 1–2 business days.
            </p>
          </div>

          <div className="p-6 rounded-card bg-sand/40 border border-hairline space-y-3">
            <div className="w-10 h-10 rounded-full bg-ivory-light border border-hairline flex items-center justify-center text-champagne-dark">
              <Truck className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-obsidian">2–4 Day Transit</h3>
            <p className="text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
              Sialkot, Lahore, Karachi, Islamabad, and Rawalpindi receive packages within 2–3 business days. Nationwide transit takes 3–4 days.
            </p>
          </div>

          <div className="p-6 rounded-card bg-sand/40 border border-hairline space-y-3">
            <div className="w-10 h-10 rounded-full bg-ivory-light border border-hairline flex items-center justify-center text-champagne-dark">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-obsidian">Complimentary Freight</h3>
            <p className="text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
              Free nationwide delivery on all orders over {formatPKR(BRAND_CONFIG.freeShippingThreshold)}. Standard rate of {formatPKR(350)} applies below.
            </p>
          </div>
        </div>

        {/* Detailed Guidelines */}
        <div className="space-y-10 divide-y divide-hairline">
          <div className="pt-8 space-y-3">
            <h2 className="font-serif text-xl sm:text-2xl font-medium text-obsidian">
              Cash on Delivery (COD) Procedure
            </h2>
            <p className="text-sm text-obsidian-700 leading-relaxed font-light">
              We offer frictionless Cash on Delivery across all serviceable postal codes in Pakistan. When your package arrives, our courier partner will provide your sealed luxury parcel. Payment must be rendered in cash (exact change recommended) prior to opening. If an exchange or inspection is needed, our 7-day door-to-door exchange guarantee takes immediate effect.
            </p>
          </div>

          <div className="pt-8 space-y-3">
            <h2 className="font-serif text-xl sm:text-2xl font-medium text-obsidian">
              SMS & WhatsApp Real-time Tracking
            </h2>
            <p className="text-sm text-obsidian-700 leading-relaxed font-light">
              Upon courier dispatch, a notification with your tracking number is issued via SMS and WhatsApp. You may track your package in real-time through the courier&apos;s digital tracking portal from departure to your doorstep.
            </p>
          </div>

          <div className="pt-8 space-y-3">
            <h2 className="font-serif text-xl sm:text-2xl font-medium text-obsidian">
              Remote Destinations & Special Handling
            </h2>
            <p className="text-sm text-obsidian-700 leading-relaxed font-light">
              For deliveries outside major metropolitan zones (e.g., Gilgit, Gwadar, Mirpur, Abbottabad), transit may require an additional 24–48 hours depending on courier route frequencies. All packages are insured against loss or damage in transit.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
