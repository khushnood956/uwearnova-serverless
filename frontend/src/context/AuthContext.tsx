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
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
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
          if (isMounted) setUser(me);
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
          if (isMounted) setUser(me);
        } catch {
          // ignore profile load error
        }
      } else if (event === "SIGNED_OUT") {
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
    async (data: RegisterRequest) => {
      await authApi.register(data);
      // Auto-login upon registration
      await login({ email: data.email, password: data.password });
    },
    [login]
  );

  const logout = React.useCallback(async () => {
    try {
      await authApi.logout();
    } catch (e) {
      console.warn("Logout error:", e);
    }
    setUser(null);
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
      isAuthModalOpen,
      authModalTab,
      openAuthModal,
      closeAuthModal,
    }),
    [user, isLoading, login, register, logout, isAuthModalOpen, authModalTab, openAuthModal, closeAuthModal]
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
