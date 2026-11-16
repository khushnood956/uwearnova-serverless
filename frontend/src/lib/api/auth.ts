/**
 * Customer Authentication & Identity API (Supabase Auth Backend)
 * Replaces legacy FastAPI custom JWT with Supabase GoTrue Auth.
 */

import { supabase } from "@/lib/supabase/client";
import {
  ChangePasswordRequest,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from "./types";

let cachedUserResponse: UserResponse | null = null;
let cachedAuthUserId: string | null = null;

export const authApi = {
  async register(data: RegisterRequest): Promise<UserResponse> {
    cachedUserResponse = null;
    cachedAuthUserId = null;
    const { data: authData, error } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
      options: {
        data: {
          first_name: data.first_name || "",
          last_name: data.last_name || "",
          phone: data.phone || "",
          user_type: "customer",
        },
      },
    });

    if (error) {
      throw new Error(error.message);
    }

    const user = authData.user;
    if (!user) {
      throw new Error("Registration failed to create user session.");
    }

    return {
      id: 0,
      email: user.email || data.email,
      first_name: data.first_name || null,
      last_name: data.last_name || null,
      phone: data.phone || null,
      status: "active",
      user_type: "customer",
      created_at: user.created_at || new Date().toISOString(),
      updated_at: user.updated_at || new Date().toISOString(),
    };
  },

  async login(credentials: LoginRequest): Promise<TokenResponse> {
    cachedUserResponse = null;
    cachedAuthUserId = null;
    const { data, error } = await supabase.auth.signInWithPassword({
      email: credentials.email,
      password: credentials.password,
    });

    if (error) {
      throw new Error(error.message);
    }

    if (!data.session) {
      throw new Error("No session created upon login.");
    }

    return {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      token_type: "bearer",
      expires_in: data.session.expires_in || 3600,
    };
  },

  async getMe(): Promise<UserResponse> {
    const { data: { user }, error } = await supabase.auth.getUser();

    if (error || !user) {
      cachedUserResponse = null;
      cachedAuthUserId = null;
      throw new Error(error?.message || "User is not authenticated.");
    }

    if (cachedUserResponse && cachedAuthUserId === user.id) {
      return cachedUserResponse;
    }

    // Attempt to read enriched profile from public.users / customer_profiles
    const { data: domainUser } = await supabase
      .from("users")
      .select("id, email, phone, status, user_type, created_at, updated_at, customer_profiles(first_name, last_name)")
      .eq("auth_user_id", user.id)
      .maybeSingle();

    const meta = user.user_metadata || {};
    const profile = Array.isArray(domainUser?.customer_profiles)
      ? domainUser.customer_profiles[0]
      : domainUser?.customer_profiles;

    cachedUserResponse = {
      id: domainUser?.id || 0,
      email: user.email || "",
      first_name: profile?.first_name || meta.first_name || null,
      last_name: profile?.last_name || meta.last_name || null,
      phone: domainUser?.phone || meta.phone || null,
      status: domainUser?.status || "active",
      user_type: domainUser?.user_type || meta.user_type || "customer",
      created_at: domainUser?.created_at || user.created_at || new Date().toISOString(),
      updated_at: domainUser?.updated_at || user.updated_at || new Date().toISOString(),
    };
    cachedAuthUserId = user.id;

    return cachedUserResponse;
  },

  async logout(_refreshToken?: string): Promise<void> {
    cachedUserResponse = null;
    cachedAuthUserId = null;
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.warn("Supabase signOut error:", error.message);
    }
  },

  async changePassword(data: ChangePasswordRequest): Promise<void> {
    const { error } = await supabase.auth.updateUser({
      password: data.new_password,
    });

    if (error) {
      throw new Error(error.message);
    }
  },
};
