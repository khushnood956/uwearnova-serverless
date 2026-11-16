"use client";

import * as React from "react";
import { Breadcrumbs } from "@/components/common/Breadcrumbs";
import { BRAND_CONFIG } from "@/lib/brand";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Phone, Mail, MapPin, Clock, Check, MessageSquare } from "lucide-react";

export default function ContactPage() {
  const [sent, setSent] = React.useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSent(true);
    setTimeout(() => setSent(false), 5000);
  };

  return (
    <main className="flex-1 pb-20 bg-ivory">
      <div className="container-site pt-6 pb-4">
        <Breadcrumbs items={[{ label: "Contact Us" }]} />
      </div>

      <div className="container-site max-w-5xl py-6 space-y-12">
        {/* Header */}
        <div className="border-b border-hairline pb-8">
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Direct Concierge
          </span>
          <h1 className="font-serif text-3xl sm:text-4xl lg:text-h2 font-medium text-obsidian tracking-tight mt-2">
            Connect With Our Atelier
          </h1>
          <p className="text-sm sm:text-base text-obsidian-600 mt-3 font-light leading-relaxed">
            Our styling and sizing team in Sialkot, Pakistan is at your personal disposal for bespoke guidance, order tracking, and fitting advice.
          </p>
        </div>

        {/* Split Layout: Atelier on Ink, Form on Ivory */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Atelier Details (Ink Panel) */}
          <div className="lg:col-span-5 bg-obsidian text-ivory rounded-card p-8 sm:p-10 space-y-8 shadow-card">
            <div>
              <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne">
                Physical Atelier
              </span>
              <h3 className="font-serif text-2xl font-medium text-ivory-light mt-1">
                Sialkot Studio & Atelier
              </h3>
              <p className="text-xs sm:text-sm text-ivory-dark/70 font-light mt-2 leading-relaxed">
                By private appointment for custom tailoring, export capsules, or bespoke viewings.
              </p>
            </div>

            <div className="space-y-4 text-xs sm:text-sm text-ivory/80 font-light">
              <div className="flex items-start gap-3">
                <MapPin className="w-4 h-4 text-champagne shrink-0 mt-0.5" />
                <span>Sialkot, Punjab, Pakistan</span>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="w-4 h-4 text-champagne shrink-0" />
                <span>{BRAND_CONFIG.contact.phone}</span>
              </div>
              <div className="flex items-center gap-3">
                <Mail className="w-4 h-4 text-champagne shrink-0" />
                <span>{BRAND_CONFIG.contact.email}</span>
              </div>
              <div className="flex items-start gap-3">
                <Clock className="w-4 h-4 text-champagne shrink-0 mt-0.5" />
                <span>{BRAND_CONFIG.contact.supportHours}</span>
              </div>
            </div>

            <div className="pt-4 border-t border-obsidian-800">
              <a
                href={BRAND_CONFIG.socials.whatsapp}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center w-full h-12 px-5 rounded-button bg-champagne hover:bg-champagne-light text-obsidian font-semibold text-xs tracking-wider uppercase gap-2.5 transition-colors duration-fast shadow-subtle"
              >
                <MessageSquare className="w-4 h-4" />
                <span>WhatsApp Styling Concierge</span>
              </a>
            </div>
          </div>

          {/* Inquiry Form (Ivory Card) */}
          <div className="lg:col-span-7 bg-ivory-light rounded-card border border-hairline p-8 sm:p-10 shadow-subtle space-y-6">
            <div>
              <span className="text-[11px] font-semibold tracking-[0.18em] uppercase text-champagne-dark">
                Direct Inquiry
              </span>
              <h3 className="font-serif text-2xl font-medium text-obsidian mt-1">
                Send an Inquiry
              </h3>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input label="Your Full Name" required placeholder="Ahmad Khan" />
              <Input label="Email Address" type="email" required placeholder="name@example.com" />
              <Input label="WhatsApp / Contact Number" placeholder="0319 1772713" />

              <div className="space-y-1.5 text-left">
                <label className="block text-[11px] font-semibold uppercase tracking-[0.16em] text-obsidian-600">
                  Your Message or Sizing Inquiry
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Share details about your requested size, order reference, or styling question..."
                  className="w-full px-4 py-3 rounded-card text-sm bg-sand/20 text-obsidian border border-hairline focus:border-champagne focus:ring-1 focus:ring-champagne focus:outline-none transition-colors duration-fast font-light placeholder:text-obsidian-400"
                />
              </div>

              <Button type="submit" variant="primary" size="lg" className="w-full mt-2">
                Submit Inquiry
              </Button>

              {sent && (
                <div className="p-4 rounded-card bg-obsidian text-ivory text-xs flex items-center gap-2.5 transition-opacity duration-fast">
                  <Check className="w-4 h-4 text-champagne shrink-0" />
                  <span>Your message has been received. Our concierge will reply within 4 hours.</span>
                </div>
              )}
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
