"use client";

import * as React from "react";
import {
  X,
  Lock,
  Mail,
  User as UserIcon,
  Phone,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Inbox,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { BRAND_CONFIG } from "@/lib/brand";
import { authApi } from "@/lib/api/auth";

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

  // Email verification required step
  const [verificationPendingEmail, setVerificationPendingEmail] = React.useState<string | null>(null);
  const [resendStatus, setResendStatus] = React.useState<"idle" | "sending" | "sent" | "error">("idle");
  const [resendMsg, setResendMsg] = React.useState<string | null>(null);

  React.useEffect(() => {
    setActiveTab(authModalTab);
    setErrorMsg(null);
    setVerificationPendingEmail(null);
    setResendStatus("idle");
    setResendMsg(null);
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
        const res = await register({
          email,
          password,
          first_name: firstName.trim() || undefined,
          last_name: lastName.trim() || undefined,
          phone: phone.trim() || undefined,
        });

        if (res?.requiresVerification) {
          setVerificationPendingEmail(email);
        }
      }
    } catch (err: any) {
      const msg = err.message || "Failed to process request. Please check your credentials.";
      if (msg.toLowerCase().includes("email not confirmed") || msg.toLowerCase().includes("not verified")) {
        setVerificationPendingEmail(email);
      } else {
        setErrorMsg(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendVerification = async () => {
    if (!verificationPendingEmail) return;
    setResendStatus("sending");
    setResendMsg(null);
    try {
      await authApi.resendVerificationEmail(verificationPendingEmail);
      setResendStatus("sent");
      setResendMsg("A new verification link has been delivered to your inbox.");
    } catch (err: any) {
      setResendStatus("error");
      setResendMsg(err.message || "Unable to resend verification email at this time.");
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
              {verificationPendingEmail
                ? "Verify your email address to activate your account."
                : activeTab === "signin"
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

        {/* Verification Pending Guided View */}
        {verificationPendingEmail ? (
          <div className="p-6 space-y-5 animate-fade-in">
            <div className="w-14 h-14 rounded-full bg-champagne-light text-champagne-dark border border-champagne-dark/20 flex items-center justify-center mx-auto shadow-inner">
              <Inbox className="w-7 h-7" />
            </div>

            <div className="text-center space-y-1.5">
              <h3 className="font-serif text-lg font-medium text-obsidian">
                Verify Your Email Address
              </h3>
              <p className="text-xs text-obsidian-600 max-w-xs mx-auto leading-relaxed">
                We sent a secure verification link to{" "}
                <span className="font-semibold text-obsidian">{verificationPendingEmail}</span>.
              </p>
            </div>

            {/* Guided steps */}
            <div className="p-4 bg-ivory-sand/50 rounded-xl border border-hairline space-y-3 text-xs text-obsidian-700">
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-obsidian text-ivory flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                  1
                </span>
                <span>Open your inbox and look for an email from <strong>{BRAND_CONFIG.name}</strong>.</span>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-obsidian text-ivory flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                  2
                </span>
                <span>Click the <strong>Confirm Email / Verify Account</strong> button to verify your identity.</span>
              </div>
              <div className="flex items-start gap-2.5">
                <span className="w-5 h-5 rounded-full bg-obsidian text-ivory flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                  3
                </span>
                <span>If you don’t see it in 1–2 minutes, check your <strong>Spam / Junk</strong> folder.</span>
              </div>
            </div>

            {resendMsg && (
              <div
                className={`p-3 text-xs rounded-button flex items-start gap-2 border ${
                  resendStatus === "sent"
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : "bg-crimson/5 text-crimson border-crimson/20"
                }`}
              >
                {resendStatus === "sent" ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                )}
                <span>{resendMsg}</span>
              </div>
            )}

            <div className="space-y-2 pt-2">
              <button
                type="button"
                onClick={handleResendVerification}
                disabled={resendStatus === "sending"}
                className="w-full py-2.5 px-4 rounded-button border border-obsidian text-obsidian text-xs font-semibold hover:bg-obsidian hover:text-ivory transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${resendStatus === "sending" ? "animate-spin" : ""}`} />
                <span>{resendStatus === "sending" ? "Sending Link..." : "Resend Verification Email"}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setVerificationPendingEmail(null);
                  setActiveTab("signin");
                }}
                className="w-full py-2.5 text-xs text-obsidian-600 hover:text-obsidian font-medium flex items-center justify-center gap-1"
              >
                <span>Return to Sign In</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
  );
}
