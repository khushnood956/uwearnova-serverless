import { cache } from "react";
import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder-project.supabase.co";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.placeholder";

/**
 * Deduplicated Server Supabase Client for React Server Components.
 * Wrapped in React cache() so multiple components in the same request
 * cycle share the exact same client instance and cookie store.
 */
export const createServerSupabaseClient = cache(async () => {
  const cookieStore = await cookies();

  return createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      get(name: string) {
        return cookieStore.get(name)?.value;
      },
      set(name: string, value: string, options: CookieOptions) {
        try {
          cookieStore.set({ name, value, ...options });
        } catch {
          // Can be safely ignored if middleware is managing session cookies
        }
      },
      remove(name: string, options: CookieOptions) {
        try {
          cookieStore.set({ name, value: "", ...options });
        } catch {
          // Can be safely ignored if middleware is managing session cookies
        }
      },
    },
  });
});

/**
 * Deduplicated current user fetcher for Server Components.
 * Wrapped in React cache() so multiple calls in the same request
 * (e.g. layout, header, page) share a single remote network round-trip.
 */
export const getServerUser = cache(async () => {
  const supabase = await createServerSupabaseClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  if (error || !user) {
    return null;
  }
  return user;
});

/**
 * Deduplicated current session fetcher for Server Components.
 */
export const getServerSession = cache(async () => {
  const supabase = await createServerSupabaseClient();
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();
  if (error || !session) {
    return null;
  }
  return session;
});
