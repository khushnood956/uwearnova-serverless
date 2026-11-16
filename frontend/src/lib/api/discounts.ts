import { supabase } from "@/lib/supabase/client";

export interface CouponItem {
  id: number;
  code: string;
  discount_type: "percentage" | "fixed_amount";
  discount_value: number;
  minimum_order_amount: number;
  usage_limit?: number | null;
  usage_count: number;
  valid_from: string;
  valid_until?: string | null;
  is_active: boolean;
}

export interface CouponCreateInput {
  code: string;
  discount_type: "percentage" | "fixed_amount";
  discount_value: number;
  minimum_order_amount?: number;
  usage_limit?: number | null;
}

export const discountsApi = {
  async getCoupons(): Promise<CouponItem[]> {
    const { data, error } = await supabase
      .from("coupons")
      .select("*")
      .order("created_at", { ascending: false });

    if (error) throw new Error(error.message);
    return data || [];
  },

  async createCoupon(input: CouponCreateInput): Promise<CouponItem> {
    const codeClean = input.code.trim().toUpperCase();

    const { data, error } = await supabase
      .from("coupons")
      .insert({
        code: codeClean,
        discount_type: input.discount_type,
        discount_value: input.discount_value,
        minimum_order_amount: input.minimum_order_amount || 0,
        usage_limit: input.usage_limit || null,
        is_active: true,
      })
      .select()
      .single();

    if (error) throw new Error(error.message);
    return data;
  },

  async toggleCouponStatus(id: number, isActive: boolean): Promise<void> {
    const { error } = await supabase
      .from("coupons")
      .update({ is_active: isActive })
      .eq("id", id);

    if (error) throw new Error(error.message);
  },

  async deleteCoupon(id: number): Promise<void> {
    const { error } = await supabase.from("coupons").delete().eq("id", id);
    if (error) throw new Error(error.message);
  },

  async validatePromoCode(
    code: string,
    cartSubtotal: number
  ): Promise<{
    valid: boolean;
    code: string;
    discount_amount: number;
    discount_type: string;
    discount_value: number;
    message?: string;
  }> {
    const clean = code.trim().toUpperCase();
    const { data, error } = await supabase
      .from("coupons")
      .select("*")
      .eq("code", clean)
      .eq("is_active", true)
      .maybeSingle();

    if (error || !data) {
      return {
        valid: false,
        code: clean,
        discount_amount: 0,
        discount_type: "percentage",
        discount_value: 0,
        message: "Invalid or inactive promo code.",
      };
    }

    if (data.minimum_order_amount && cartSubtotal < Number(data.minimum_order_amount)) {
      return {
        valid: false,
        code: clean,
        discount_amount: 0,
        discount_type: data.discount_type,
        discount_value: Number(data.discount_value),
        message: `Order subtotal must be at least Rs. ${data.minimum_order_amount} to apply code ${clean}.`,
      };
    }

    let discountAmount = 0;
    if (data.discount_type === "percentage") {
      discountAmount = Math.round((cartSubtotal * Number(data.discount_value)) / 100);
    } else {
      discountAmount = Math.min(cartSubtotal, Number(data.discount_value));
    }

    return {
      valid: true,
      code: clean,
      discount_amount: discountAmount,
      discount_type: data.discount_type,
      discount_value: Number(data.discount_value),
      message: `Promo code ${clean} successfully applied!`,
    };
  },
};
