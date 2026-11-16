import { supabase } from "@/lib/supabase/client";

export interface PaymentMethodConfig {
  enabled: boolean;
  title: string;
  description: string;
  details?: string;
}

export interface StoreBundle {
  id: string;
  name: string;
  description: string;
  badge?: string;
  item_count: number;
  discount_percentage: number;
  fixed_price?: number;
  is_active: boolean;
}

export interface DynamicStoreSettings {
  delivery_fee: number;
  free_shipping_threshold: number;
  payment_methods: {
    cod: PaymentMethodConfig;
    card: PaymentMethodConfig;
    bank_transfer: PaymentMethodConfig;
  };
  bundles: StoreBundle[];
}

export const DEFAULT_STORE_SETTINGS: DynamicStoreSettings = {
  delivery_fee: 350,
  free_shipping_threshold: 5000,
  payment_methods: {
    cod: {
      enabled: true,
      title: "Cash on Delivery (COD)",
      description: "Pay in cash to courier rider upon inspecting package integrity at doorstep.",
    },
    card: {
      enabled: false,
      title: "Credit / Debit Card (Online)",
      description: "Pay securely with Visa, MasterCard, or PayPak cards via payment gateway.",
    },
    bank_transfer: {
      enabled: false,
      title: "Direct Bank Transfer / IBFT",
      description: "Transfer directly to corporate atelier account (Meezan / HBL).",
      details: "Meezan Bank Ltd | Account: 02100109283746 | Title: UWEARNOVA LUXURY",
    },
  },
  bundles: [
    {
      id: "duo_linen",
      name: "Atelier Linen Duo",
      description: "Pair any 2 Signature Linen pieces and receive complimentary bespoke pocket square + 15% off.",
      badge: "Curated Bundle",
      item_count: 2,
      discount_percentage: 15,
      is_active: true,
    },
    {
      id: "festive_trio",
      name: "Festive Capsule Wardrobe",
      description: "Complete ceremonial look: Embroidered Kurta, Raw Silk Trouser & Silk Shawl.",
      badge: "Exclusive Trio",
      item_count: 3,
      discount_percentage: 20,
      is_active: true,
    },
  ],
};

let memoryCache: { settings: DynamicStoreSettings; fetchedAt: number } | null = null;
const CACHE_TTL_MS = 15000; // 15 seconds

export const settingsApi = {
  async getSettings(): Promise<DynamicStoreSettings> {
    const now = Date.now();
    if (memoryCache && now - memoryCache.fetchedAt < CACHE_TTL_MS) {
      return memoryCache.settings;
    }

    try {
      const { data, error } = await supabase
        .from("audit_logs")
        .select("changes")
        .eq("entity_type", "store_settings")
        .eq("entity_id", "default")
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (error || !data || !data.changes) {
        return DEFAULT_STORE_SETTINGS;
      }

      const merged: DynamicStoreSettings = {
        delivery_fee: Number(data.changes.delivery_fee ?? DEFAULT_STORE_SETTINGS.delivery_fee),
        free_shipping_threshold: Number(data.changes.free_shipping_threshold ?? DEFAULT_STORE_SETTINGS.free_shipping_threshold),
        payment_methods: {
          cod: { ...DEFAULT_STORE_SETTINGS.payment_methods.cod, ...(data.changes.payment_methods?.cod || {}) },
          card: { ...DEFAULT_STORE_SETTINGS.payment_methods.card, ...(data.changes.payment_methods?.card || {}) },
          bank_transfer: { ...DEFAULT_STORE_SETTINGS.payment_methods.bank_transfer, ...(data.changes.payment_methods?.bank_transfer || {}) },
        },
        bundles: Array.isArray(data.changes.bundles) && data.changes.bundles.length > 0
          ? data.changes.bundles
          : DEFAULT_STORE_SETTINGS.bundles,
      };

      memoryCache = { settings: merged, fetchedAt: now };
      return merged;
    } catch {
      return DEFAULT_STORE_SETTINGS;
    }
  },

  async updateSettings(newSettings: DynamicStoreSettings, actorEmail?: string): Promise<DynamicStoreSettings> {
    memoryCache = null;

    // 1. Persist to audit_logs store_settings snapshot
    const { error } = await supabase.from("audit_logs").insert({
      action: "SETTINGS_UPDATE",
      entity_type: "store_settings",
      entity_id: "default",
      actor_email: actorEmail || "admin@uwearnova.com",
      changes: newSettings,
    });

    if (error) {
      throw new Error(`Failed to save settings: ${error.message}`);
    }

    // 2. Also update database shipping_methods base_rate for consistency
    try {
      await supabase
        .from("shipping_methods")
        .update({
          base_rate: newSettings.delivery_fee,
          free_threshold: newSettings.free_shipping_threshold,
        })
        .neq("id", -1);
    } catch {
      // ignore
    }

    memoryCache = { settings: newSettings, fetchedAt: Date.now() };
    return newSettings;
  },
};
