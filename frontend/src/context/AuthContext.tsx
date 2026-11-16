"use client";

import * as React from "react";
import { authApi } from "@/lib/api/auth";
import { cartApi } from "@/lib/api/cart";
import { getAnonymousCartToken } from "@/lib/api/client";
import { LoginRequest, RegisterRequest, UserResponse } from "@/lib/api/types";
import { supabase } from "@/lib/supabase/client";

interface AuthContextType {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<{ requiresVerification?: boolean }>;
  logout: () => Promise<void>;
  updateProfile: (data: { first_name?: string; last_name?: string; phone?: string }) => Promise<void>;
  changePassword: (newPassword: string) => Promise<void>;
  refreshUser: () => Promise<void>;
  isAuthModalOpen: boolean;
  authModalTab: "signin" | "register";
  openAuthModal: (tab?: "signin" | "register") => void;
  closeAuthModal: () => void;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = React.useState(false);
  const [authModalTab, setAuthModalTab] = React.useState<"signin" | "register">("signin");

  // Load authenticated session on mount and subscribe to auth changes
  React.useEffect(() => {
    let isMounted = true;

    async function checkInitialSession() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session && isMounted) {
          const me = await authApi.getMe();
          if (isMounted) {
            setUser(me);
            if (me?.user_type) {
              document.cookie = `uwear_user_role=${me.user_type}; path=/; max-age=2592000; SameSite=Lax`;
              try {
                localStorage.setItem("uwear_user_role", me.user_type);
              } catch {}
            }
          }
        } else {
          document.cookie = "uwear_user_role=; path=/; max-age=0; SameSite=Lax";
          try {
            localStorage.removeItem("uwear_user_role");
          } catch {}
        }
      } catch {
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    checkInitialSession();

    // Listen to real-time auth events (token refresh, sign-in, sign-out)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (!isMounted) return;

      if (event === "SIGNED_IN" && session) {
        try {
          const me = await authApi.getMe();
          if (isMounted) {
            setUser(me);
            if (me?.user_type) {
              document.cookie = `uwear_user_role=${me.user_type}; path=/; max-age=2592000; SameSite=Lax`;
              try {
                localStorage.setItem("uwear_user_role", me.user_type);
              } catch {}
            }
          }
        } catch {
          // ignore profile load error
        }
      } else if (event === "SIGNED_OUT") {
        document.cookie = "uwear_user_role=; path=/; max-age=0; SameSite=Lax";
        try {
          localStorage.removeItem("uwear_user_role");
        } catch {}
        if (isMounted) setUser(null);
      }
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const login = React.useCallback(async (credentials: LoginRequest) => {
    await authApi.login(credentials);
    const currentUser = await authApi.getMe();
    setUser(currentUser);

    // Synchronize role cookie and local storage immediately
    if (currentUser?.user_type) {
      document.cookie = `uwear_user_role=${currentUser.user_type}; path=/; max-age=2592000; SameSite=Lax`;
      try {
        localStorage.setItem("uwear_user_role", currentUser.user_type);
      } catch {}
    }

    // Role-based portal redirection: Admins and Staff are routed to workstations immediately
    if (currentUser?.user_type === "admin") {
      setIsAuthModalOpen(false);
      window.location.href = "/admin";
      return;
    }

    if (currentUser?.user_type === "staff") {
      setIsAuthModalOpen(false);
      window.location.href = "/staff";
      return;
    }

    // Merge anonymous guest cart into customer account if guest cart exists
    const guestCartToken = getAnonymousCartToken();
    if (guestCartToken) {
      try {
        await cartApi.mergeCart(guestCartToken);
      } catch (e) {
        console.warn("Guest cart merge error after login:", e);
      }
    }

    setIsAuthModalOpen(false);
  }, []);

  const register = React.useCallback(
    async (data: RegisterRequest): Promise<{ requiresVerification?: boolean }> => {
      await authApi.register(data);
      // Attempt auto-login upon registration
      try {
        await login({ email: data.email, password: data.password });
        return { requiresVerification: false };
      } catch (err: any) {
        // If Supabase confirms email confirmation is required:
        const msg = (err?.message || "").toLowerCase();
        if (msg.includes("confirm") || msg.includes("not verified") || msg.includes("verification")) {
          return { requiresVerification: true };
        }
        // If login failed for other reason, assume email verification is required
        return { requiresVerification: true };
      }
    },
    [login]
  );

  const logout = React.useCallback(async () => {
    document.cookie = "uwear_user_role=; path=/; max-age=0; SameSite=Lax";
    try {
      localStorage.removeItem("uwear_user_role");
    } catch {}
    try {
      await authApi.logout();
    } catch (e) {
      console.warn("Logout error:", e);
    }
    setUser(null);
    window.location.href = "/";
  }, []);

  const updateProfile = React.useCallback(
    async (data: { first_name?: string; last_name?: string; phone?: string }) => {
      const updated = await authApi.updateProfile(data);
      setUser(updated);
    },
    []
  );

  const changePassword = React.useCallback(async (newPassword: string) => {
    await authApi.changePassword({ new_password: newPassword });
  }, []);

  const refreshUser = React.useCallback(async () => {
    const fresh = await authApi.getMe();
    setUser(fresh);
  }, []);

  const openAuthModal = React.useCallback((tab: "signin" | "register" = "signin") => {
    setAuthModalTab(tab);
    setIsAuthModalOpen(true);
  }, []);

  const closeAuthModal = React.useCallback(() => {
    setIsAuthModalOpen(false);
  }, []);

  const value = React.useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      updateProfile,
      changePassword,
      refreshUser,
      isAuthModalOpen,
      authModalTab,
      openAuthModal,
      closeAuthModal,
    }),
    [
      user,
      isLoading,
      login,
      register,
      logout,
      updateProfile,
      changePassword,
      refreshUser,
      isAuthModalOpen,
      authModalTab,
      openAuthModal,
      closeAuthModal,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
