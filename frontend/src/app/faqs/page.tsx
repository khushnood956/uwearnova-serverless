import Link from "next/link";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { ProductAccordion } from "@/components/product/ProductAccordion";
import { BRAND_CONFIG } from "@/lib/brand";
import { MessageSquare } from "lucide-react";

export const metadata = {
  title: "Frequently Asked Questions | UWEARNOVA",
  description: "Common questions regarding sizing, payments, delivery, and textiles at UWEARNOVA.",
};

export default function FAQPage() {
  const faqs = [
    {
      id: "faq-1",
      title: "How does Cash on Delivery (COD) operate?",
      content:
        "Cash on Delivery is supported across all serviceable postal codes in Pakistan. You simply hand exact cash payment to the delivery rider once your sealed parcel arrives. If an exchange is desired, our 7-day door-to-door exchange guarantee takes effect immediately.",
    },
    {
      id: "faq-2",
      title: "What are your nationwide dispatch & delivery timelines?",
      content:
        "Orders are prepared and dispatched within 24–48 hours from our Sialkot fulfillment atelier. Major hubs (Sialkot, Rawalpindi) typically receive deliveries within 2–3 business days. Other cities and regions take 3–4 business days.",
    },
    {
      id: "faq-3",
      title: "How do I choose the flawless size and fit?",
      content:
        "Every piece includes an accurate Size Guide showing chest, waist, sleeve, and length measurements in both inches and centimeters. If you sit between two sizes, we suggest choosing the larger size for our relaxed architectural silhouettes.",
    },
    {
      id: "faq-4",
      title: "How does the 7-day complimentary doorstep exchange work?",
      content:
        "Simply message our WhatsApp concierge at " +
        BRAND_CONFIG.contact.phone +
        " with your order reference. Our courier partner will deliver your replacement piece directly to your door while collecting the original piece simultaneously. No post office queues or return shipping fees.",
    },
    {
      id: "faq-5",
      title: "Where are UWEARNOVA garments and footwear crafted?",
      content:
        "Our collections are conceptualized and patterned in our Sialkot design studio. Tailoring is completed across master artisanal workshops in Pakistan using ethically sourced virgin wool blends, Egyptian Giza cottons, Mulberry silks, and full-grain calfskin leathers.",
    },
    {
      id: "faq-6",
      title: "Can I modify or cancel my order after placement?",
      content:
        "Because orders enter our atelier packing stream within a few hours, please contact our concierge via WhatsApp immediately if you need to adjust shipping details, size, or cancel before courier handover.",
    },
  ];

  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-4">
        <Breadcrumbs items={[{ label: "Frequently Asked Questions" }]} />
      </div>

      <div className="container-site py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-start">
          {/* Left Column (Sticky on desktop) */}
          <div className="lg:col-span-5 lg:sticky lg:top-28 space-y-6">
            <div>
              <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
                Client Care & Guidance
              </span>
              <h1 className="font-serif text-3xl sm:text-4xl lg:text-h2 font-medium text-obsidian tracking-tight mt-2 leading-[1.1]">
                Frequently Asked Questions
              </h1>
              <p className="text-sm sm:text-base text-obsidian-600 mt-4 font-light leading-relaxed">
                Everything you need to know about our luxury tailoring, nationwide door-to-door delivery, and concierge support.
              </p>
            </div>

            <div className="p-6 rounded-card bg-sand/40 border border-hairline space-y-3">
              <h3 className="font-serif text-lg font-medium text-obsidian">
                Have a bespoke question?
              </h3>
              <p className="text-xs sm:text-sm text-obsidian-600 font-light leading-relaxed">
                Our atelier styling concierge is available Monday to Saturday, 10 AM to 8 PM PKT.
              </p>
              <Link
                href="/contact"
                className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-obsidian hover:text-champagne-dark transition-colors duration-fast pt-1"
              >
                <MessageSquare className="w-3.5 h-3.5 text-champagne-dark" />
                <span>Contact Client Concierge</span>
              </Link>
            </div>
          </div>

          {/* Right Column (Accordion with hairline styling) */}
          <div className="lg:col-span-7">
            <ProductAccordion items={faqs} />
          </div>
        </div>
      </div>
    </main>
  );
}
