"use client";

import * as React from "react";
import { Modal } from "@/components/ui/Modal";
import { CategorySlug } from "@/types/product";

interface SizeGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
  category: CategorySlug;
}

export function SizeGuideModal({
  isOpen,
  onClose,
  category,
}: SizeGuideModalProps) {
  const [unit, setUnit] = React.useState<"in" | "cm">("in");

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Measurement & Size Guide"
      description="Standardized tailoring measurements. If you fall between sizes, we recommend ordering one size up for an editorial relaxed silhouette."
      className="max-w-xl"
    >
      <div className="space-y-4">
        {/* Unit Toggle */}
        <div className="flex justify-end">
          <div className="inline-flex rounded-lg border border-ivory-dark p-0.5 bg-ivory/60 text-xs">
            <button
              onClick={() => setUnit("in")}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                unit === "in"
                  ? "bg-white text-obsidian shadow-xs"
                  : "text-obsidian-600 hover:text-obsidian"
              }`}
            >
              Inches (in)
            </button>
            <button
              onClick={() => setUnit("cm")}
              className={`px-3 py-1 rounded-md font-medium transition-colors ${
                unit === "cm"
                  ? "bg-white text-obsidian shadow-xs"
                  : "text-obsidian-600 hover:text-obsidian"
              }`}
            >
              Centimeters (cm)
            </button>
          </div>
        </div>

        {/* Size Table */}
        <div className="overflow-x-auto rounded-lg border border-ivory-dark">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-ivory text-obsidian-700 font-serif">
              <tr>
                <th className="py-2.5 px-3">Size</th>
                <th className="py-2.5 px-3">Chest / Bust</th>
                <th className="py-2.5 px-3">Waist</th>
                <th className="py-2.5 px-3">Shoulder</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ivory-dark/60 text-obsidian">
              {unit === "in" ? (
                <>
                  <tr>
                    <td className="py-2 px-3 font-semibold">S</td>
                    <td className="py-2 px-3">36 - 38</td>
                    <td className="py-2 px-3">30 - 32</td>
                    <td className="py-2 px-3">17.5</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">M</td>
                    <td className="py-2 px-3">39 - 41</td>
                    <td className="py-2 px-3">33 - 35</td>
                    <td className="py-2 px-3">18.5</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">L</td>
                    <td className="py-2 px-3">42 - 44</td>
                    <td className="py-2 px-3">36 - 38</td>
                    <td className="py-2 px-3">19.5</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">XL</td>
                    <td className="py-2 px-3">45 - 47</td>
                    <td className="py-2 px-3">39 - 41</td>
                    <td className="py-2 px-3">20.5</td>
                  </tr>
                </>
              ) : (
                <>
                  <tr>
                    <td className="py-2 px-3 font-semibold">S</td>
                    <td className="py-2 px-3">91 - 96</td>
                    <td className="py-2 px-3">76 - 81</td>
                    <td className="py-2 px-3">44.5</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">M</td>
                    <td className="py-2 px-3">99 - 104</td>
                    <td className="py-2 px-3">84 - 89</td>
                    <td className="py-2 px-3">47.0</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">L</td>
                    <td className="py-2 px-3">106 - 112</td>
                    <td className="py-2 px-3">91 - 96</td>
                    <td className="py-2 px-3">49.5</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold">XL</td>
                    <td className="py-2 px-3">114 - 119</td>
                    <td className="py-2 px-3">99 - 104</td>
                    <td className="py-2 px-3">52.0</td>
                  </tr>
                </>
              )}
            </tbody>
          </table>
        </div>

        <p className="text-[11px] text-obsidian-500 leading-relaxed">
          Need personalized fitting advice? Reach our Sialkot atelier via WhatsApp for bespoke size consultations.
        </p>
      </div>
    </Modal>
  );
}
