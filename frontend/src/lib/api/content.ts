/**
 * Storefront Editorial & CMS Content API (Supabase Backend)
 */

import { supabase } from "@/lib/supabase/client";

export interface ContentPageResponse {
  id: number;
  slug: string;
  title: string;
  body: string;
  meta_title?: string | null;
  meta_description?: string | null;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementBarResponse {
  id: number;
  message: string;
  link_url?: string | null;
  link_text?: string | null;
  bg_color?: string | null;
  text_color?: string | null;
  is_active: boolean;
  start_at?: string | null;
  end_at?: string | null;
}

export interface HomepageCampaignResponse {
  id: number;
  title: string;
  subtitle?: string | null;
  cta_text?: string | null;
  cta_link?: string | null;
  image_url?: string | null;
  display_order: number;
  is_active: boolean;
}

export const contentApi = {
  async getPage(slug: string): Promise<ContentPageResponse> {
    const { data, error } = await supabase
      .from("content_pages")
      .select("*")
      .eq("slug", slug)
      .eq("is_published", true)
      .single();

    if (error || !data) {
      throw new Error(error?.message || `Content page '${slug}' not found`);
    }

    return data;
  },

  async getAnnouncements(): Promise<AnnouncementBarResponse[]> {
    const { data } = await supabase
      .from("announcement_bars")
      .select("*")
      .eq("is_active", true)
      .order("display_order", { ascending: true });

    return (data || []).map((ab: any) => ({
      id: ab.id,
      message: ab.text,
      link_url: ab.link_url,
      link_text: "Learn more",
      is_active: ab.is_active,
    }));
  },

  async getHomepageCampaigns(): Promise<HomepageCampaignResponse[]> {
    const { data } = await supabase
      .from("homepage_campaigns")
      .select("*")
      .eq("is_active", true)
      .order("sort_order", { ascending: true });

    return (data || []).map((hc: any) => ({
      id: hc.id,
      title: hc.title,
      subtitle: hc.subtitle,
      cta_text: hc.cta_text,
      cta_link: hc.cta_url,
      image_url: hc.image_url,
      display_order: hc.sort_order,
      is_active: hc.is_active,
    }));
  },
};
