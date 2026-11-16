"use client";

import * as React from "react";
import { X, Lock, Mail, User as UserIcon, Phone, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { BRAND_CONFIG } from "@/lib/brand";

export function AuthModal() {
  const { isAuthModalOpen, authModalTab, closeAuthModal, login, register } = useAuth();

  const [activeTab, setActiveTab] = React.useState<"signin" | "register">("signin");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [firstName, setFirstName] = React.useState("");
  const [lastName, setLastName] = React.useState("");
  const [phone, setPhone] = React.useState("");

  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    setActiveTab(authModalTab);
    setErrorMsg(null);
  }, [authModalTab, isAuthModalOpen]);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      if (activeTab === "signin") {
        await login({ email, password });
      } else {
        await register({
          email,
          password,
          first_name: firstName.trim() || undefined,
          last_name: lastName.trim() || undefined,
          phone: phone.trim() || undefined,
        });
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to process request. Please check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-obsidian/70 backdrop-blur-sm animate-fade-in"
    >
      {/* Backdrop */}
      <div className="fixed inset-0" onClick={closeAuthModal} />

      {/* Modal Card */}
      <div className="relative w-full max-w-md bg-ivory rounded-card border border-hairline shadow-subtle z-10 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-hairline">
          <div>
            <h2 className="font-serif text-2xl font-medium tracking-tight text-obsidian">
              {BRAND_CONFIG.name}
            </h2>
            <p className="text-xs text-obsidian-600 mt-0.5">
              {activeTab === "signin"
                ? "Sign in to access your luxury wardrobe and saved pieces."
                : "Create an account for personalized styling and order tracking."}
            </p>
          </div>
          <button
            type="button"
            onClick={closeAuthModal}
            className="p-1.5 text-obsidian-500 hover:text-obsidian rounded-button transition-colors duration-fast"
            aria-label="Close authentication modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-hairline bg-ivory-sand/40">
          <button
            type="button"
            onClick={() => {
              setActiveTab("signin");
              setErrorMsg(null);
            }}
            className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider transition-colors duration-fast ${
              activeTab === "signin"
                ? "text-obsidian border-b-2 border-champagne bg-ivory"
                : "text-obsidian-500 hover:text-obsidian"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab("register");
              setErrorMsg(null);
            }}
            className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider transition-colors duration-fast ${
              activeTab === "register"
                ? "text-obsidian border-b-2 border-champagne bg-ivory"
                : "text-obsidian-500 hover:text-obsidian"
            }`}
          >
            Register
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 text-xs text-crimson bg-crimson/5 border border-crimson/20 rounded-button flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {activeTab === "register" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-obsidian-700 mb-1">
                  First Name
                </label>
                <div className="relative">
                  <UserIcon className="absolute left-3 top-2.5 w-4 h-4 text-obsidian-400" />
                  <input
                    type="text"
                    required
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="Amina"
                    className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-hairline rounded-button focus:outline-none focus:ring-1 focus:ring-champagne"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-obsidian-700 mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Khan"
                  className="w-full px-3 py-2 text-sm bg-white border border-hairline rounded-button focus:outline-none focus:ring-1 focus:ring-champagne"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-obsidian-700 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-2.5 w-4 h-4 text-obsidian-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="amina.khan@example.com"
                className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-hairline rounded-button focus:outline-none focus:ring-1 focus:ring-champagne"
              />
            </div>
          </div>

          {activeTab === "register" && (
            <div>
              <label className="block text-xs font-medium text-obsidian-700 mb-1">
                Mobile Number (optional)
              </label>
              <div className="relative">
                <Phone className="absolute left-3 top-2.5 w-4 h-4 text-obsidian-400" />
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+92 300 1234567"
                  className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-hairline rounded-button focus:outline-none focus:ring-1 focus:ring-champagne"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-obsidian-700 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 w-4 h-4 text-obsidian-400" />
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-hairline rounded-button focus:outline-none focus:ring-1 focus:ring-champagne"
              />
            </div>
            {activeTab === "register" && (
              <p className="text-[11px] text-obsidian-500 mt-1">
                Must be at least 8 characters with letters and numbers.
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-3 px-4 bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider rounded-button hover:bg-obsidian-800 transition-colors duration-fast disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : activeTab === "signin" ? (
              "Sign In to Account"
            ) : (
              "Create Customer Account"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
