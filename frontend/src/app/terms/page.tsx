import { Metadata } from "next";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { BRAND_CONFIG, formatPKR } from "@/lib/brand";
import { contentApi } from "@/lib/api/content";

export const metadata: Metadata = {
  title: `Terms & Conditions | ${BRAND_CONFIG.name}`,
  description: "Terms and conditions of purchase, delivery, and exchange at UWEARNOVA.",
};

export default async function TermsPage() {
  let backendPage = null;
  try {
    backendPage = await contentApi.getPage("terms");
  } catch {
    // Fallback
  }

  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-4">
        <Breadcrumbs items={[{ label: "Terms & Conditions" }]} />
      </div>

      <div className="container-site max-w-4xl py-6 space-y-10">
        <div className="border-b border-hairline pb-8">
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Store Policies
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-h2 font-medium text-obsidian tracking-tight mt-2">
            {backendPage?.title || "Terms & Conditions of Service"}
          </h1>
          <p className="text-sm sm:text-base text-obsidian-600 mt-3 font-light leading-relaxed">
            Please review the contractual terms governing orders, pricing, dispatch timelines, and doorstep exchanges.
          </p>
        </div>

        {backendPage?.body ? (
          <div
            className="prose prose-sm max-w-none text-obsidian-700 leading-relaxed font-light"
            dangerouslySetInnerHTML={{ __html: backendPage.body }}
          />
        ) : (
          <div className="space-y-8 text-xs sm:text-sm text-obsidian-700 font-light leading-relaxed divide-y divide-hairline">
            <div className="space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">1. Ordering & Contract Formation</h2>
              <p>
                By placing an order via our website, you agree to these Terms. An order constitutes an offer to purchase luxury apparel or accessories. Our acceptance occurs upon dispatch of the physical consignment from our atelier, at which point an SMS or email tracking update is provided.
              </p>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">2. Pricing & Currency</h2>
              <p>
                All prices are stated in Pakistani Rupees (PKR) and include applicable taxes. We reserve the right to correct accidental pricing errors before order dispatch. If a pricing error occurs, we will contact you before shipment.
              </p>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">3. Shipping & Delivery Terms</h2>
              <p>
                Standard courier delivery rates are dynamically displayed during checkout. Complimentary delivery applies automatically to qualifying domestic orders meeting the store threshold. Estimated transit timelines are 2–4 business days across major urban hubs. Delivery times are estimates provided by domestic courier partners and may vary during national holidays or adverse transit conditions.
              </p>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">4. Cash on Delivery (COD) Rules</h2>
              <p>
                Cash on Delivery orders must be paid in full to the courier representative before opening the parcel seal. Orders submitted with fictitious contact information or unconfirmed numbers are subject to verification cancellation prior to dispatch.
              </p>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">5. 7-Day Doorstep Exchange Policy</h2>
              <p>
                Garments and footwear may be exchanged within 7 calendar days of receipt provided items are unwashed, unworn, and retain original luxury tags and packaging. Exchange requests can be lodged via the Customer Account Portal or WhatsApp Concierge.
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
