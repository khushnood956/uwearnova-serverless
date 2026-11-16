import { Metadata } from "next";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { BRAND_CONFIG } from "@/lib/brand";
import { contentApi } from "@/lib/api/content";

export const metadata: Metadata = {
  title: `Privacy Policy | ${BRAND_CONFIG.name}`,
  description: "Privacy and data protection policy for UWEARNOVA customers in Pakistan.",
};

export default async function PrivacyPolicyPage() {
  let backendPage = null;
  try {
    backendPage = await contentApi.getPage("privacy-policy");
  } catch {
    // Fallback to static policy content
  }

  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-4">
        <Breadcrumbs items={[{ label: "Privacy Policy" }]} />
      </div>

      <div className="container-site max-w-4xl py-6 space-y-10">
        <div className="border-b border-hairline pb-8">
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Data Governance & Trust
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-h2 font-medium text-obsidian tracking-tight mt-2">
            {backendPage?.title || "Privacy & Data Protection Policy"}
          </h1>
          <p className="text-sm sm:text-base text-obsidian-600 mt-3 font-light leading-relaxed">
            How UWEARNOVA collects, uses, and protects client personal details and delivery information across Pakistan.
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
              <h2 className="font-serif text-xl font-medium text-obsidian">1. Information We Collect</h2>
              <p>
                When you browse our catalogue, register a customer account, or place an order via Cash on Delivery or digital payment, we collect personal information necessary to fulfill your purchases:
              </p>
              <ul className="list-disc list-inside space-y-1.5 pl-2">
                <li>Recipient Full Name, contact email, and mobile telephone number.</li>
                <li>Physical delivery address (street address, city, postal code, and delivery landmarks).</li>
                <li>Order history, consignment tracking references, and return/exchange records.</li>
                <li>Communication preferences (SMS delivery alerts, WhatsApp concierge correspondence).</li>
              </ul>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">2. Purpose of Data Processing</h2>
              <p>
                Your data is strictly utilized to deliver and improve our luxury fashion services:
              </p>
              <ul className="list-disc list-inside space-y-1.5 pl-2">
                <li>Processing and packing orders at our Sialkot fulfillment atelier.</li>
                <li>Handing over delivery consignments to verified domestic courier partners (Trax, Leopards, TCS).</li>
                <li>Sending SMS dispatch notifications and rider delivery coordination calls.</li>
                <li>Coordinating 7-day doorstep exchanges and processing verified refunds.</li>
                <li>Safeguarding accounts against brute-force intrusion and preventing checkout fraud.</li>
              </ul>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">3. Third-Party Courier & Payment Integration</h2>
              <p>
                We only transmit necessary logistics details (recipient name, address, telephone, and payable COD amount) to authorized domestic courier partners for the express purpose of package delivery. We do not sell, rent, or monetize customer data to third-party marketing brokers.
              </p>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">4. Account Security & Session Privacy</h2>
              <p>
                Passwords are hashed using industry-standard Argon2id cryptographic algorithms. Customers maintain full control over active login sessions and can revoke remote sessions at any time through the Customer Account Security Portal.
              </p>
            </div>

            <div className="pt-6 space-y-3">
              <h2 className="font-serif text-xl font-medium text-obsidian">5. Concierge Contact</h2>
              <p>
                For inquiries regarding personal data retention or to request account deletion, contact our privacy officer at{" "}
                <a href={`mailto:${BRAND_CONFIG.contact.email}`} className="text-champagne-dark font-medium underline">
                  {BRAND_CONFIG.contact.email}
                </a>.
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
