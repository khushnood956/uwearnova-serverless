import { supabase } from "@/lib/supabase/client";

export interface PaymentMethodConfig {
  enabled: boolean;
  title: string;
  description: string;
  details?: string;
}

export interface BankTransferConfig extends PaymentMethodConfig {
  bank_name?: string;
  account_title?: string;
  account_number?: string;
  iban?: string;
  branch?: string;
  instructions?: string;
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
    bank_transfer: BankTransferConfig;
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
      bank_name: "Meezan Bank Ltd",
      account_title: "UWEARNOVA LUXURY ATELIER",
      account_number: "02100109283746",
      iban: "PK36MEZN0002100109283746",
      branch: "Sialkot Cantt Branch",
      instructions: "Please send payment confirmation screenshot via WhatsApp to +92 300 0000000 or email support@uwearnova.com with your Order Number.",
      details: "Meezan Bank Ltd | Account: 02100109283746 | Title: UWEARNOVA LUXURY ATELIER | IBAN: PK36MEZN0002100109283746",
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
const CACHE_TTL_MS = 10000; // 10 seconds

export const settingsApi = {
  async getSettings(): Promise<DynamicStoreSettings> {
    const now = Date.now();
    if (memoryCache && now - memoryCache.fetchedAt < CACHE_TTL_MS) {
      return memoryCache.settings;
    }

    try {
      // 1. Primary: read from public.store_settings (has public read RLS policy)
      const { data: storeRow, error: storeErr } = await supabase
        .from("store_settings")
        .select("value")
        .eq("key", "general_config")
        .maybeSingle();

      let changes = storeRow?.value;

      // 2. Secondary: fallback to audit_logs snapshot if store_settings was empty
      if (!changes || storeErr) {
        const { data: auditRow } = await supabase
          .from("audit_logs")
          .select("changes")
          .eq("entity_type", "store_settings")
          .eq("entity_id", "default")
          .order("created_at", { ascending: false })
          .limit(1)
          .maybeSingle();

        changes = auditRow?.changes;
      }

      if (!changes) {
        return DEFAULT_STORE_SETTINGS;
      }

      const merged: DynamicStoreSettings = {
        delivery_fee: Number(changes.delivery_fee ?? DEFAULT_STORE_SETTINGS.delivery_fee),
        free_shipping_threshold: Number(changes.free_shipping_threshold ?? DEFAULT_STORE_SETTINGS.free_shipping_threshold),
        payment_methods: {
          cod: { ...DEFAULT_STORE_SETTINGS.payment_methods.cod, ...(changes.payment_methods?.cod || {}) },
          card: { ...DEFAULT_STORE_SETTINGS.payment_methods.card, ...(changes.payment_methods?.card || {}) },
          bank_transfer: { ...DEFAULT_STORE_SETTINGS.payment_methods.bank_transfer, ...(changes.payment_methods?.bank_transfer || {}) },
        },
        bundles: Array.isArray(changes.bundles) && changes.bundles.length > 0
          ? changes.bundles
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

    // Format details field for bank transfer
    const bt = newSettings.payment_methods.bank_transfer;
    if (bt) {
      const parts = [
        bt.bank_name ? `Bank: ${bt.bank_name}` : null,
        bt.account_title ? `Title: ${bt.account_title}` : null,
        bt.account_number ? `A/C: ${bt.account_number}` : null,
        bt.iban ? `IBAN: ${bt.iban}` : null,
        bt.branch ? `Branch: ${bt.branch}` : null,
      ].filter(Boolean);
      bt.details = parts.join(" | ");
    }

    // 1. Prefer API endpoint which uses service role client (completely immune to RLS restrictions)
    try {
      const res = await fetch("/api/admin/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings: newSettings, actorEmail }),
      });

      if (res.ok) {
        memoryCache = { settings: newSettings, fetchedAt: Date.now() };
        return newSettings;
      }
    } catch {
      // fallback to direct client call if fetch fails (e.g. non-browser environment)
    }

    // 2. Direct Supabase fallback
    const { error: storeErr } = await supabase
      .from("store_settings")
      .upsert({
        key: "general_config",
        value: newSettings,
        updated_at: new Date().toISOString(),
        updated_by: actorEmail || "admin@uwearnova.com",
      });

    if (storeErr) {
      throw new Error(`Failed to save settings: ${storeErr.message}`);
    }

    try {
      await supabase.from("audit_logs").insert({
        action: "SETTINGS_UPDATE",
        entity_type: "store_settings",
        entity_id: "default",
        actor_email: actorEmail || "admin@uwearnova.com",
        changes: newSettings,
      });
    } catch {
      // Non-fatal
    }

    try {
      await supabase
        .from("shipping_methods")
        .update({
          base_rate: newSettings.delivery_fee,
          free_threshold: newSettings.free_shipping_threshold,
          updated_at: new Date().toISOString(),
        })
        .neq("id", -1);
    } catch {
      // Non-fatal
    }

    memoryCache = { settings: newSettings, fetchedAt: Date.now() };
    return newSettings;
  },
};
