import { NextRequest, NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { DEFAULT_STORE_SETTINGS, DynamicStoreSettings } from "@/lib/api/settings";

export async function GET() {
  try {
    const supabaseAdmin = createAdminClient();

    // 1. Fetch from public.store_settings
    const { data: storeRow } = await supabaseAdmin
      .from("store_settings")
      .select("value")
      .eq("key", "general_config")
      .maybeSingle();

    if (storeRow?.value) {
      return NextResponse.json(storeRow.value);
    }

    // 2. Fallback to audit_logs snapshot
    const { data: auditRow } = await supabaseAdmin
      .from("audit_logs")
      .select("changes")
      .eq("entity_type", "store_settings")
      .eq("entity_id", "default")
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (auditRow?.changes) {
      return NextResponse.json(auditRow.changes);
    }

    return NextResponse.json(DEFAULT_STORE_SETTINGS);
  } catch (err: any) {
    return NextResponse.json(DEFAULT_STORE_SETTINGS);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { settings, actorEmail } = body as { settings: DynamicStoreSettings; actorEmail?: string };

    if (!settings) {
      return NextResponse.json({ error: "Settings object is required." }, { status: 400 });
    }

    const supabaseAdmin = createAdminClient();

    // Format details field for bank transfer if present
    const bt = settings.payment_methods?.bank_transfer;
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

    // 1. Upsert into public.store_settings table
    const { error: storeErr } = await supabaseAdmin
      .from("store_settings")
      .upsert({
        key: "general_config",
        value: settings,
        updated_at: new Date().toISOString(),
        updated_by: actorEmail || "admin@uwearnova.com",
      });

    if (storeErr) {
      console.error("Failed to upsert store_settings:", storeErr.message);
      return NextResponse.json({ error: `Database error: ${storeErr.message}` }, { status: 500 });
    }

    // 2. Insert audit log record with admin privileges
    try {
      await supabaseAdmin.from("audit_logs").insert({
        action: "SETTINGS_UPDATE",
        entity_type: "store_settings",
        entity_id: "default",
        actor_email: actorEmail || "admin@uwearnova.com",
        changes: settings,
      });
    } catch (auditErr: any) {
      console.warn("Audit log insert warning:", auditErr.message);
    }

    // 3. Update shipping_methods table
    try {
      await supabaseAdmin
        .from("shipping_methods")
        .update({
          base_rate: settings.delivery_fee,
          free_threshold: settings.free_shipping_threshold,
          updated_at: new Date().toISOString(),
        })
        .neq("id", -1);
    } catch (shipErr: any) {
      console.warn("Shipping methods update warning:", shipErr.message);
    }

    return NextResponse.json({ success: true, settings });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Failed to update settings" }, { status: 500 });
  }
}
