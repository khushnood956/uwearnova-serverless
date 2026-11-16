/**
 * Storefront Shipping & Delivery API (Supabase Backend)
 */

import { supabase } from "@/lib/supabase/client";

export interface DeliveryAddressValidationRequest {
  full_name: string;
  phone: string;
  address_line_1: string;
  address_line_2?: string | null;
  city: string;
  postal_code?: string | null;
  country_code?: string;
}

export interface DeliveryAddressValidationResponse {
  is_valid: boolean;
  city: string;
  is_serviceable: boolean;
  zone_code?: string | null;
  normalized_phone: string;
  message?: string | null;
}

export interface ShippingQuoteRequest {
  city: string;
  postal_code?: string | null;
  country_code?: string;
  subtotal?: number;
  is_cod?: boolean;
}

export interface ShippingMethodQuoteItem {
  code: string;
  name: string;
  description?: string | null;
  estimated_days_min: number;
  estimated_days_max: number;
  is_cod_supported: boolean;
  base_fee: number;
  discount: number;
  final_fee: number;
  is_free: boolean;
  free_shipping_threshold?: number | null;
  amount_needed_for_free_shipping?: number | null;
}

export interface ShippingQuoteResponse {
  destination_city: string;
  is_serviceable: boolean;
  zone_code?: string | null;
  subtotal: number;
  available_methods: ShippingMethodQuoteItem[];
  recommended_method_code: string;
}

export const shippingApi = {
  async getQuote(data: ShippingQuoteRequest): Promise<ShippingQuoteResponse> {
    const subtotal = Number(data.subtotal || 0);

    const { data: methods } = await supabase
      .from("shipping_methods")
      .select("*")
      .eq("is_active", true);

    // Read dynamic settings (or fallback to database shipping_methods rate)
    let dynamicBaseFee = 350;
    let dynamicFreeThreshold = 5000;
    try {
      const { settingsApi } = await import("@/lib/api/settings");
      const currentSettings = await settingsApi.getSettings();
      dynamicBaseFee = currentSettings.delivery_fee;
      dynamicFreeThreshold = currentSettings.free_shipping_threshold;
    } catch {
      // fallback
    }

    const quoteMethods: ShippingMethodQuoteItem[] = (methods && methods.length > 0 ? methods : [{
      code: "standard",
      name: "Standard Nationwide Courier Delivery",
      estimated_days: "2-4 business days",
    }]).map((m: any) => {
      // Prioritize live dynamic settings configured by administrator
      const baseFee = Number(dynamicBaseFee || m.base_rate || 350);
      const freeThreshold = Number(dynamicFreeThreshold || m.free_threshold || 5000);
      const isFree = subtotal >= freeThreshold;
      const finalFee = isFree ? 0.00 : baseFee;

      return {
        code: m.code,
        name: m.name,
        description: m.estimated_days,
        estimated_days_min: 2,
        estimated_days_max: 4,
        is_cod_supported: true,
        base_fee: baseFee,
        discount: isFree ? baseFee : 0,
        final_fee: finalFee,
        is_free: isFree,
        free_shipping_threshold: freeThreshold,
        amount_needed_for_free_shipping: Math.max(0, freeThreshold - subtotal),
      };
    });

    if (quoteMethods.length === 0) {
      const isFree = subtotal >= dynamicFreeThreshold;
      quoteMethods.push({
        code: "standard",
        name: "Standard Delivery",
        description: "2-4 business days",
        estimated_days_min: 2,
        estimated_days_max: 4,
        is_cod_supported: true,
        base_fee: dynamicBaseFee,
        discount: isFree ? dynamicBaseFee : 0,
        final_fee: isFree ? 0.00 : dynamicBaseFee,
        is_free: isFree,
        free_shipping_threshold: dynamicFreeThreshold,
        amount_needed_for_free_shipping: Math.max(0, dynamicFreeThreshold - subtotal),
      });
    }

    return {
      destination_city: data.city || "Karachi",
      is_serviceable: true,
      zone_code: "PK-DOMESTIC",
      subtotal,
      available_methods: quoteMethods,
      recommended_method_code: quoteMethods[0]?.code || "standard",
    };
  },

  async validateAddress(data: DeliveryAddressValidationRequest): Promise<DeliveryAddressValidationResponse> {
    const cleanPhone = data.phone.replace(/[\s\-\(\)]/g, "");
    const isValidPhone = /^(\+92|03)[0-9]{9}$/.test(cleanPhone);
    const isValidCity = Boolean(data.city && data.city.trim().length >= 2);

    return {
      is_valid: isValidPhone && isValidCity,
      city: data.city,
      is_serviceable: true,
      zone_code: "PK-DOMESTIC",
      normalized_phone: cleanPhone,
      message: isValidPhone ? null : "Please enter a valid Pakistani mobile number (e.g., 03001234567).",
    };
  },
};
