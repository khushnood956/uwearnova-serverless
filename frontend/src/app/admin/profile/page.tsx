"use client";

import * as React from "react";
import {
  UserCheck,
  Lock,
  KeyRound,
  Shield,
  Eye,
  EyeOff,
  CheckCircle,
  AlertCircle,
  Sparkles,
  Phone,
  Mail,
  User as UserIcon,
  ShieldAlert,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function AdminProfileSecurityPage() {
  const { user, updateProfile, changePassword } = useAuth();

  // Profile / Display Name Form
  const [firstName, setFirstName] = React.useState("");
  const [lastName, setLastName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [profileSaving, setProfileSaving] = React.useState(false);
  const [profileSuccess, setProfileSuccess] = React.useState<string | null>(null);
  const [profileError, setProfileError] = React.useState<string | null>(null);

  // Change Password Form
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [passwordSaving, setPasswordSaving] = React.useState(false);
  const [passwordSuccess, setPasswordSuccess] = React.useState<string | null>(null);
  const [passwordError, setPasswordError] = React.useState<string | null>(null);

  // Initialize from active user session
  React.useEffect(() => {
    if (user) {
      setFirstName(user.first_name || "");
      setLastName(user.last_name || "");
      setPhone(user.phone || "");
    }
  }, [user]);

  const isSuperAdmin = user?.email === "admin1@uwearnova.com";

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError(null);
    setProfileSuccess(null);
    setProfileSaving(true);

    try {
      await updateProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone: phone.trim() || undefined,
      });
      setProfileSuccess("Display name and contact details updated successfully.");
      setTimeout(() => setProfileSuccess(null), 5000);
    } catch (err: any) {
      setProfileError(err.message || "Failed to update profile display name.");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setPasswordSaving(true);
    try {
      await changePassword(newPassword);
      setPasswordSuccess("Administrative password successfully updated.");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setPasswordSuccess(null), 5000);
    } catch (err: any) {
      setPasswordError(err.message || "Failed to update password. Please try again.");
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-champagne-dark mb-1">
          <UserCheck className="w-4 h-4" />
          <span>Security & Identity Console</span>
        </div>
        <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight">
          Profile & Security Settings
        </h1>
        <p className="text-xs text-obsidian-600 font-light mt-1">
          Configure your administrative display name and rotate your system credentials.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Forms */}
        <div className="lg:col-span-7 space-y-6">
          {/* 1. Display Name & Personal Identity Card */}
          <div className="bg-ivory-light border border-hairline rounded-2xl p-6 sm:p-8 shadow-card space-y-6">
            <div className="flex items-center justify-between border-b border-hairline pb-4">
              <div>
                <h2 className="font-serif text-lg font-medium text-obsidian">Display Identity</h2>
                <p className="text-xs text-obsidian-500 font-light">
                  Set how your name appears across the administrative console and staff logs.
                </p>
              </div>
              <span className="p-2 rounded-lg bg-champagne/10 text-champagne-dark">
                <UserIcon className="w-5 h-5" />
              </span>
            </div>

            {profileSuccess && (
              <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{profileSuccess}</span>
              </div>
            )}

            {profileError && (
              <div className="p-3.5 rounded-lg bg-crimson/10 border border-crimson/20 text-crimson text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{profileError}</span>
              </div>
            )}

            <form onSubmit={handleProfileSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-[11px] font-semibold text-obsidian-700 uppercase tracking-wider">
                    First Name / Title
                  </label>
                  <input
                    type="text"
                    required
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="e.g. Lead Administrator"
                    className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-hairline text-obsidian focus:outline-none focus:border-champagne focus:ring-1 focus:ring-champagne"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] font-semibold text-obsidian-700 uppercase tracking-wider">
                    Last Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="e.g. Director"
                    className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-hairline text-obsidian focus:outline-none focus:border-champagne focus:ring-1 focus:ring-champagne"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[11px] font-semibold text-obsidian-700 uppercase tracking-wider">
                  Contact Phone
                </label>
                <div className="relative">
                  <Phone className="w-4 h-4 absolute left-3 top-3 text-obsidian-400" />
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+92 319 1772713"
                    className="w-full pl-9 pr-3.5 py-2.5 rounded-lg bg-white border border-hairline text-obsidian focus:outline-none focus:border-champagne focus:ring-1 focus:ring-champagne"
                  />
                </div>
              </div>

              {/* Live Preview Card */}
              <div className="p-3.5 rounded-xl bg-ivory-sand/60 border border-hairline space-y-1">
                <p className="text-[10px] uppercase tracking-wider font-semibold text-obsidian-500">Sidebar Preview</p>
                <p className="text-xs font-semibold text-obsidian">
                  {firstName.trim() ? `${firstName} ${lastName}`.trim() : user?.email}
                </p>
                <p className="text-[11px] text-obsidian-500">{user?.email}</p>
              </div>

              <button
                type="submit"
                disabled={profileSaving}
                className="w-full py-2.5 px-4 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors disabled:opacity-50"
              >
                {profileSaving ? "Saving Identity..." : "Save Display Name"}
              </button>
            </form>
          </div>

          {/* 2. Change Password Card */}
          <div className="bg-ivory-light border border-hairline rounded-2xl p-6 sm:p-8 shadow-card space-y-6">
            <div className="flex items-center justify-between border-b border-hairline pb-4">
              <div>
                <h2 className="font-serif text-lg font-medium text-obsidian">Change Administrative Password</h2>
                <p className="text-xs text-obsidian-500 font-light">
                  Rotate your administrative account password to keep your store console secure.
                </p>
              </div>
              <span className="p-2 rounded-lg bg-champagne/10 text-champagne-dark">
                <KeyRound className="w-5 h-5" />
              </span>
            </div>

            {passwordSuccess && (
              <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{passwordSuccess}</span>
              </div>
            )}

            {passwordError && (
              <div className="p-3.5 rounded-lg bg-crimson/10 border border-crimson/20 text-crimson text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{passwordError}</span>
              </div>
            )}

            <form onSubmit={handlePasswordSubmit} className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="block text-[11px] font-semibold text-obsidian-700 uppercase tracking-wider">
                  New Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full pr-10 pl-3.5 py-2.5 rounded-lg bg-white border border-hairline text-obsidian focus:outline-none focus:border-champagne focus:ring-1 focus:ring-champagne"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3 top-2.5 text-obsidian-400 hover:text-obsidian"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-[11px] font-semibold text-obsidian-700 uppercase tracking-wider">
                  Confirm New Password
                </label>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={8}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-hairline text-obsidian focus:outline-none focus:border-champagne focus:ring-1 focus:ring-champagne"
                />
              </div>

              <button
                type="submit"
                disabled={passwordSaving}
                className="w-full py-2.5 px-4 rounded-button bg-champagne-dark text-white text-xs font-semibold uppercase tracking-wider hover:bg-champagne transition-colors disabled:opacity-50"
              >
                {passwordSaving ? "Updating Password..." : "Update Password"}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Clearance & Authority Overview */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-obsidian text-ivory rounded-2xl p-6 sm:p-8 space-y-6 border border-obsidian-800 shadow-card">
            <div className="flex items-center gap-2 text-champagne text-xs font-semibold uppercase tracking-wider">
              <Shield className="w-4 h-4" />
              <span>Authority & Role Tier</span>
            </div>

            <div>
              <div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-champagne text-obsidian mb-2">
                {isSuperAdmin ? "★ Super Administrator" : "Store Administrator"}
              </div>
              <h3 className="font-serif text-xl font-medium text-white">
                {isSuperAdmin ? "Principal Lead Authority" : "Store Management Authority"}
              </h3>
              <p className="text-xs text-ivory-light/70 font-light mt-1.5 leading-relaxed">
                {isSuperAdmin
                  ? "You hold unrestricted authority across UWEARNOVA, including administrative staff creation and role delegation."
                  : "You have full operational control over Catalog, POS Counter, Rates & Settings, and Orders."}
              </p>
            </div>

            <div className="space-y-3 pt-2 border-t border-white/10 text-xs text-ivory-light/80">
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">Account Email:</span>
                <span className="font-medium text-ivory truncate max-w-[200px]">{user?.email}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">Staff Creation Access:</span>
                <span className={isSuperAdmin ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                  {isSuperAdmin ? "Authorized (Full)" : "Reserved for Super Admin"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">Store Settings & Rates:</span>
                <span className="text-emerald-400 font-semibold">Authorized (Full)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">POS Counter & Inventory:</span>
                <span className="text-emerald-400 font-semibold">Authorized (Full)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">Order Operations & COD:</span>
                <span className="text-emerald-400 font-semibold">Authorized (Full)</span>
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 text-[11px] text-ivory-light/50 font-light leading-relaxed">
              Security standard: NIST SP 800-63B compliant authentication via Supabase GoTrue Auth.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
