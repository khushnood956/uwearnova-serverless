"use client";

import * as React from "react";
import Link from "next/link";
import {
  UserCheck,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle,
  AlertCircle,
  Phone,
  User as UserIcon,
  ArrowLeft,
  Briefcase,
  Shield,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function StaffProfileSecurityPage() {
  const { user, updateProfile, changePassword } = useAuth();

  // Profile Form
  const [firstName, setFirstName] = React.useState("");
  const [lastName, setLastName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [profileSaving, setProfileSaving] = React.useState(false);
  const [profileSuccess, setProfileSuccess] = React.useState<string | null>(null);
  const [profileError, setProfileError] = React.useState<string | null>(null);

  // Password Form
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [passwordSaving, setPasswordSaving] = React.useState(false);
  const [passwordSuccess, setPasswordSuccess] = React.useState<string | null>(null);
  const [passwordError, setPasswordError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (user) {
      setFirstName(user.first_name || "");
      setLastName(user.last_name || "");
      setPhone(user.phone || "");
    }
  }, [user]);

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
      setProfileSuccess("Display name and contact information updated.");
      setTimeout(() => setProfileSuccess(null), 5000);
    } catch (err: any) {
      setProfileError(err.message || "Failed to update profile name.");
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match.");
      return;
    }

    setPasswordSaving(true);
    try {
      await changePassword(newPassword);
      setPasswordSuccess("Staff account password successfully updated.");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setPasswordSuccess(null), 5000);
    } catch (err: any) {
      setPasswordError(err.message || "Failed to change password. Please try again.");
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header with Back Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <Link
            href="/staff"
            className="inline-flex items-center gap-1.5 text-xs text-champagne-dark hover:underline font-semibold uppercase tracking-wider mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Work Queue</span>
          </Link>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight">
            Staff Profile & Password
          </h1>
          <p className="text-xs text-obsidian-600 font-light mt-1">
            Update your operational staff display name and change your login credentials.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-obsidian text-champagne">
            {user?.email}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Forms */}
        <div className="lg:col-span-7 space-y-6">
          {/* Display Name Card */}
          <div className="bg-ivory-light border border-hairline rounded-2xl p-6 sm:p-8 shadow-card space-y-6">
            <div className="flex items-center justify-between border-b border-hairline pb-4">
              <div>
                <h2 className="font-serif text-lg font-medium text-obsidian">Staff Identity & Name</h2>
                <p className="text-xs text-obsidian-500 font-light">
                  Set how your name appears on packing slips, inventory logs, and POS receipts.
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
                    First Name
                  </label>
                  <input
                    type="text"
                    required
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="e.g. Tariq"
                    className="w-full px-3.5 py-2.5 rounded-lg bg-white border border-hairline text-obsidian focus:outline-none focus:border-champagne focus:ring-1 focus:ring-champagne"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-[11px] font-semibold text-obsidian-700 uppercase tracking-wider">
                    Last Name
                  </label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="e.g. Cashier"
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

              {/* Live Preview */}
              <div className="p-3.5 rounded-xl bg-ivory-sand/60 border border-hairline space-y-1">
                <p className="text-[10px] uppercase tracking-wider font-semibold text-obsidian-500">Live Header Preview</p>
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
                {profileSaving ? "Saving..." : "Save Staff Display Name"}
              </button>
            </form>
          </div>

          {/* Change Password Card */}
          <div className="bg-ivory-light border border-hairline rounded-2xl p-6 sm:p-8 shadow-card space-y-6">
            <div className="flex items-center justify-between border-b border-hairline pb-4">
              <div>
                <h2 className="font-serif text-lg font-medium text-obsidian">Change Password</h2>
                <p className="text-xs text-obsidian-500 font-light">
                  Rotate your staff password to protect order queues and POS counters.
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

        {/* Right Column: Workstation & Role Info */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-obsidian text-ivory rounded-2xl p-6 sm:p-8 space-y-6 border border-obsidian-800 shadow-card">
            <div className="flex items-center gap-2 text-champagne text-xs font-semibold uppercase tracking-wider">
              <Briefcase className="w-4 h-4" />
              <span>Assigned Workstation</span>
            </div>

            <div>
              <div className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-champagne-dark text-ivory mb-2">
                Operations Staff
              </div>
              <h3 className="font-serif text-xl font-medium text-white">
                Fulfillment & Counter Operations
              </h3>
              <p className="text-xs text-ivory-light/70 font-light mt-1.5 leading-relaxed">
                Authorized for counter point-of-sale transactions, barcode scanning, consignment dispatch booking, and warehouse inventory intakes.
              </p>
            </div>

            <div className="space-y-3 pt-2 border-t border-white/10 text-xs text-ivory-light/80">
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">Staff Email:</span>
                <span className="font-medium text-ivory truncate max-w-[200px]">{user?.email}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">POS Counter Clearance:</span>
                <span className="text-emerald-400 font-semibold">Active (/admin/pos)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">Product Inventory:</span>
                <span className="text-emerald-400 font-semibold">Active (/admin/products)</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ivory-light/50">Operations Queues:</span>
                <span className="text-emerald-400 font-semibold">Active (/staff)</span>
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 text-[11px] text-ivory-light/50 font-light leading-relaxed">
              Atelier Location: Sialkot, Punjab, Pakistan • Supabase Tokyo Authenticated
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
