import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { RefreshCw, MessageSquare, PackageCheck, Truck } from "lucide-react";
import { BRAND_CONFIG } from "@/lib/brand";

export const metadata = {
  title: "Exchanges & Returns | UWEARNOVA",
  description: "Complimentary 7-day doorstep exchange and return policy across Pakistan.",
};

export default function ReturnsExchangesPage() {
  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-4">
        <Breadcrumbs items={[{ label: "Exchanges & Returns" }]} />
      </div>

      <div className="container-site max-w-4xl py-6 space-y-12">
        {/* Header */}
        <div className="border-b border-hairline pb-8">
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Confidence & Care
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-h2 font-medium text-obsidian tracking-tight mt-2">
            7-Day Doorstep Exchange Policy
          </h1>
          <p className="text-sm sm:text-base text-obsidian-600 mt-3 font-light leading-relaxed">
            We ensure an effortless fit with door-to-door courier exchanges anywhere in Pakistan. If your size isn&apos;t flawless, we swap it at your doorstep.
          </p>
        </div>

        {/* Hero Banner Callout on Sand */}
        <div className="p-6 sm:p-8 rounded-card bg-sand/40 border border-hairline flex flex-col sm:flex-row items-start sm:items-center gap-5">
          <div className="w-12 h-12 rounded-full bg-ivory-light border border-hairline flex items-center justify-center text-champagne-dark shrink-0">
            <RefreshCw className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="font-serif text-lg sm:text-xl font-medium text-obsidian">
              Zero-Friction Doorstep Swap Guarantee
            </h3>
            <p className="text-xs sm:text-sm text-obsidian-700 font-light leading-relaxed">
              Our courier brings your replacement piece directly to your door and collects the original piece simultaneously. No post office queues, no return labels, no shipping charges.
            </p>
          </div>
        </div>

        {/* Step-by-Step Exchange Timeline */}
        <div className="space-y-6">
          <div className="border-b border-hairline pb-3">
            <span className="text-[11px] font-semibold tracking-[0.18em] uppercase text-champagne-dark">
              Simple 3-Step Process
            </span>
            <h2 className="font-serif text-2xl font-medium text-obsidian mt-1">
              How to Initiate an Exchange
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
            <div className="relative p-6 rounded-card bg-ivory-light border border-hairline space-y-3">
              <div className="w-8 h-8 rounded-full bg-obsidian text-ivory text-xs font-semibold flex items-center justify-center">
                1
              </div>
              <h4 className="font-serif text-base font-medium text-obsidian">
                Notify Our Concierge
              </h4>
              <p className="text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
                Send a WhatsApp message to <strong>{BRAND_CONFIG.contact.phone}</strong> within 7 days of delivery with your order ID (UNV-XXXXXX) and desired replacement size.
              </p>
            </div>

            <div className="relative p-6 rounded-card bg-ivory-light border border-hairline space-y-3">
              <div className="w-8 h-8 rounded-full bg-obsidian text-ivory text-xs font-semibold flex items-center justify-center">
                2
              </div>
              <h4 className="font-serif text-base font-medium text-obsidian">
                Instant Dispatch
              </h4>
              <p className="text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
                Our atelier prepares your newly chosen garment and books an express reverse-swap delivery with our courier partner within 24 hours.
              </p>
            </div>

            <div className="relative p-6 rounded-card bg-ivory-light border border-hairline space-y-3">
              <div className="w-8 h-8 rounded-full bg-obsidian text-ivory text-xs font-semibold flex items-center justify-center">
                3
              </div>
              <h4 className="font-serif text-base font-medium text-obsidian">
                Doorstep Swap
              </h4>
              <p className="text-xs sm:text-sm text-obsidian-600 leading-relaxed font-light">
                Hand the initial piece (in original box and tags) to the rider upon receiving your fresh replacement piece. Simple, elegant, completed.
              </p>
            </div>
          </div>
        </div>

        {/* Eligibility Criteria */}
        <div className="pt-6 border-t border-hairline space-y-4">
          <h2 className="font-serif text-xl sm:text-2xl font-medium text-obsidian">
            Exchange Eligibility Criteria
          </h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm text-obsidian-700 font-light">
            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-champagne-dark mt-2 shrink-0" />
              <span>Garments must be unworn, unwashed, and in pristine original state.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-champagne-dark mt-2 shrink-0" />
              <span>All security tags, fabric labels, and seals must remain attached.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-champagne-dark mt-2 shrink-0" />
              <span>Footwear must be tested exclusively on carpeted surfaces with zero outsole scuffs.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-champagne-dark mt-2 shrink-0" />
              <span>Leather accessories must include original protective dust bags and boxes.</span>
            </li>
          </ul>
        </div>
      </div>
    </main>
  );
}
