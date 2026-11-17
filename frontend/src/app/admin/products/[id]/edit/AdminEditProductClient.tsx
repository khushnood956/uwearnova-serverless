"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import {
  ArrowLeft,
  Save,
  Trash2,
  Plus,
  Upload,
  Image as ImageIcon,
  CheckCircle,
  AlertCircle,
  Star,
  ExternalLink,
  Sparkles,
  Layers,
  FolderTree,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { CategoryTree, Product } from "@/lib/api/types";
import { formatPKR } from "@/lib/brand";

export default function AdminEditProductPage() {
  const params = useParams();
  const router = useRouter();
  const productId = params?.id as string;

  // Category Tree State
  const [categories, setCategories] = React.useState<CategoryTree[]>([]);
  const [selectedDeptId, setSelectedDeptId] = React.useState<number | null>(null);
  const [selectedSubcategoryId, setSelectedSubcategoryId] = React.useState<number | null>(null);

  // Loading & State
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  // Product Form State
  const [form, setForm] = React.useState({
    name: "",
    slug: "",
    subtitle: "",
    description: "",
    price: "",
    original_price: "",
    brand_label: "UWEARNOVA",
    status: "active" as "draft" | "active" | "archived",
    is_featured: false,
    is_new_arrival: false,
    is_trending: false,
  });

  // Images State
  const [images, setImages] = React.useState<any[]>([]);
  const [newImageUrl, setNewImageUrl] = React.useState("");
  const [newImageAlt, setNewImageAlt] = React.useState("");
  const [uploadingImage, setUploadingImage] = React.useState(false);
  const [uploadTab, setUploadTab] = React.useState<"file" | "url">("url");

  // Variants State
  const [variants, setVariants] = React.useState<any[]>([]);
  const [newVariant, setNewVariant] = React.useState({
    sku: "",
    size: "M",
    color_name: "Obsidian Black",
    color_hex: "#101010",
    inventory_count: 10,
    price: "",
  });
  const [showAddVariant, setShowAddVariant] = React.useState(false);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Load Product and Categories
  const loadData = React.useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    try {
      const [productData, categoryTree] = await Promise.all([
        adminApi.getProduct(productId),
        adminApi.getCategoryTree(),
      ]);

      setCategories(categoryTree);

      setForm({
        name: productData.name || "",
        slug: productData.slug || "",
        subtitle: productData.subtitle || "",
        description: productData.description || "",
        price: productData.price ? String(productData.price) : "",
        original_price: productData.original_price ? String(productData.original_price) : "",
        brand_label: productData.brand_label || "UWEARNOVA",
        status: (productData.status as any) || "active",
        is_featured: Boolean(productData.is_featured),
        is_new_arrival: Boolean(productData.is_new_arrival),
        is_trending: Boolean(productData.is_trending),
      });

      // Find category in tree to set dept / subcategory
      const catId = productData.category_id || (productData.category as any)?.id;
      if (catId) {
        let foundDeptId: number | null = null;
        let foundSubId: number | null = null;

        for (const dept of categoryTree) {
          if (Number(dept.id) === Number(catId)) {
            foundDeptId = Number(dept.id);
            break;
          }
          if (dept.children) {
            const childMatch = dept.children.find((c) => Number(c.id) === Number(catId));
            if (childMatch) {
              foundDeptId = Number(dept.id);
              foundSubId = Number(childMatch.id);
              break;
            }
          }
        }

        setSelectedDeptId(foundDeptId || (categoryTree.length > 0 ? Number(categoryTree[0].id) : null));
        setSelectedSubcategoryId(foundSubId);
      }

      setVariants(productData.variants || []);

      // Load media images
      try {
        const mediaList = await adminApi.getProductImages(productId);
        setImages(mediaList || []);
      } catch {
        setImages(productData.images || []);
      }
    } catch (err: any) {
      showNotification(err.message || "Failed to load product details", "error");
    } finally {
      setLoading(false);
    }
  }, [productId]);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const currentDept = categories.find((c) => Number(c.id) === selectedDeptId);
  const availableSubcategories = currentDept?.children || [];

  const handleDepartmentChange = (deptId: number) => {
    setSelectedDeptId(deptId);
    const dept = categories.find((c) => Number(c.id) === deptId);
    if (dept && dept.children && dept.children.length > 0) {
      setSelectedSubcategoryId(Number(dept.children[0].id));
    } else {
      setSelectedSubcategoryId(null);
    }
  };

  // Submit Product Basic Updates
  const handleSaveProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetCategoryId = selectedSubcategoryId || selectedDeptId;
    if (!targetCategoryId) {
      showNotification("Please select a department and category.", "error");
      return;
    }

    setSaving(true);
    try {
      await adminApi.updateProduct(productId, {
        name: form.name,
        slug: form.slug,
        subtitle: form.subtitle || undefined,
        description: form.description || undefined,
        category_id: targetCategoryId,
        price: Number(form.price),
        original_price: form.original_price ? Number(form.original_price) : undefined,
        brand_label: form.brand_label,
        status: form.status,
        is_featured: form.is_featured,
        is_new_arrival: form.is_new_arrival,
        is_trending: form.is_trending,
      });

      showNotification("Product details saved successfully!");
    } catch (err: any) {
      showNotification(err.message || "Failed to update product", "error");
    } finally {
      setSaving(false);
    }
  };

  // Add Image by URL
  const handleAddImageUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newImageUrl.trim()) {
      showNotification("Please enter an image URL.", "error");
      return;
    }

    setUploadingImage(true);
    try {
      const isPrimary = images.length === 0;
      const res = await adminApi.addProductImageUrl(productId, {
        image_url: newImageUrl.trim(),
        alt_text: newImageAlt.trim() || form.name,
        is_primary: isPrimary,
      });

      setNewImageUrl("");
      setNewImageAlt("");
      showNotification("Image added successfully!");

      // Refresh images
      const updatedImages = await adminApi.getProductImages(productId);
      setImages(updatedImages);
    } catch (err: any) {
      showNotification(err.message || "Failed to add image URL", "error");
    } finally {
      setUploadingImage(false);
    }
  };

  // Upload Image File(s) - Supports Multi-Image Selection
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setUploadingImage(true);
    let successCount = 0;
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("alt_text", form.name);
        formData.append("is_primary", String(images.length === 0 && i === 0));

        await adminApi.uploadProductImage(productId, formData);
        successCount++;
      }
      showNotification(
        successCount === 1
          ? "Image file uploaded successfully!"
          : `${successCount} images uploaded successfully!`
      );

      const updatedImages = await adminApi.getProductImages(productId);
      setImages(updatedImages);
      e.target.value = "";
    } catch (err: any) {
      showNotification(err.message || "Failed to upload image file(s)", "error");
      const updatedImages = await adminApi.getProductImages(productId);
      setImages(updatedImages);
    } finally {
      setUploadingImage(false);
    }
  };

  // Set Primary Image
  const handleSetPrimaryImage = async (imageId: number) => {
    try {
      await adminApi.setPrimaryProductImage(productId, imageId);
      showNotification("Primary hero image updated!");
      const updatedImages = await adminApi.getProductImages(productId);
      setImages(updatedImages);
    } catch (err: any) {
      showNotification(err.message || "Failed to set primary image", "error");
    }
  };

  // Delete Image
  const handleDeleteImage = async (imageId: number) => {
    if (!confirm("Are you sure you want to remove this image?")) return;
    try {
      await adminApi.deleteProductImage(productId, imageId);
      showNotification("Image removed.");
      const updatedImages = await adminApi.getProductImages(productId);
      setImages(updatedImages);
    } catch (err: any) {
      showNotification(err.message || "Failed to delete image", "error");
    }
  };

  // Add Variant
  const handleCreateVariant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newVariant.sku.trim()) {
      showNotification("Please provide a SKU code.", "error");
      return;
    }

    try {
      await adminApi.addVariant(productId, {
        sku: newVariant.sku.trim(),
        size: newVariant.size,
        color_name: newVariant.color_name,
        color_hex: newVariant.color_hex,
        inventory_count: Number(newVariant.inventory_count),
        price: newVariant.price ? Number(newVariant.price) : undefined,
        is_active: true,
      });

      showNotification(`SKU Variant ${newVariant.sku} added!`);
      setShowAddVariant(false);
      setNewVariant({
        sku: "",
        size: "M",
        color_name: "Obsidian Black",
        color_hex: "#101010",
        inventory_count: 10,
        price: "",
      });

      const updatedProd = await adminApi.getProduct(productId);
      setVariants(updatedProd.variants || []);
    } catch (err: any) {
      showNotification(err.message || "Failed to create variant", "error");
    }
  };

  // Delete Variant
  const handleDeleteVariant = async (variantId: number, sku: string) => {
    if (!confirm(`Are you sure you want to delete SKU variant "${sku}"?`)) return;
    try {
      await adminApi.deleteVariant(productId, variantId);
      showNotification(`Variant ${sku} deleted.`);
      const updatedProd = await adminApi.getProduct(productId);
      setVariants(updatedProd.variants || []);
    } catch (err: any) {
      showNotification(err.message || "Failed to delete variant", "error");
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-8 h-8 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-obsidian-500 font-mono">Loading product record #{productId}...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between text-xs animate-in fade-in slide-in-from-top-2 border shadow-subtle ${
            notification.type === "success"
              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
              : "bg-crimson/10 text-crimson border-crimson/20"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle className="w-4 h-4 text-emerald-600" />
            ) : (
              <AlertCircle className="w-4 h-4 text-crimson" />
            )}
            <span className="font-medium">{notification.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-xs underline hover:opacity-75"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link
            href="/admin/products"
            className="inline-flex items-center gap-1.5 text-xs text-obsidian-500 hover:text-obsidian mb-2 font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Catalogue
          </Link>
          <h1 className="font-serif text-2xl lg:text-3xl font-normal tracking-tight text-obsidian">
            Edit Piece: {form.name || `Product #${productId}`}
          </h1>
          <p className="text-xs text-obsidian-500 mt-1 font-mono">
            ID: {productId} &bull; Slug: /{form.slug}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/product/${form.slug}`}
            target="_blank"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-hairline bg-ivory-light text-obsidian text-xs font-medium hover:bg-ivory transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View on Storefront
          </Link>
          <button
            type="button"
            onClick={handleSaveProduct}
            disabled={saving}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800 transition-colors disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? "Saving..." : "Save Product Details"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column (2 cols): Details & Variants */}
        <div className="lg:col-span-2 space-y-8">
          {/* Main Details Form */}
          <form onSubmit={handleSaveProduct} className="p-6 bg-ivory-light rounded-2xl border border-hairline space-y-6">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-obsidian">Piece Information</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-obsidian-700 mb-1">
                  Product Name *
                </label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-obsidian-700 mb-1">
                    Storefront Slug *
                  </label>
                  <input
                    type="text"
                    required
                    value={form.slug}
                    onChange={(e) => setForm({ ...form, slug: e.target.value })}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white font-mono focus:outline-none focus:border-obsidian"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-obsidian-700 mb-1">
                    Subtitle / Cut Description
                  </label>
                  <input
                    type="text"
                    value={form.subtitle}
                    onChange={(e) => setForm({ ...form, subtitle: e.target.value })}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-obsidian-700 mb-1">
                  Editorial Description
                </label>
                <textarea
                  rows={4}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                />
              </div>

              {/* Department & Subcategory */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-medium text-obsidian-700 mb-1">
                    Department *
                  </label>
                  <select
                    value={selectedDeptId || ""}
                    onChange={(e) => handleDepartmentChange(Number(e.target.value))}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-obsidian-700 mb-1">
                    Subcategory / Line *
                  </label>
                  <select
                    value={selectedSubcategoryId || ""}
                    onChange={(e) => setSelectedSubcategoryId(Number(e.target.value))}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                  >
                    {availableSubcategories.map((sub) => (
                      <option key={sub.id} value={sub.id}>
                        {sub.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Pricing & Brand */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-medium text-obsidian-700 mb-1">
                    Retail Price (PKR) *
                  </label>
                  <input
                    type="number"
                    required
                    value={form.price}
                    onChange={(e) => setForm({ ...form, price: e.target.value })}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white font-mono focus:outline-none focus:border-obsidian"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-obsidian-700 mb-1">
                    Compare-At Original Price (PKR)
                  </label>
                  <input
                    type="number"
                    value={form.original_price}
                    onChange={(e) => setForm({ ...form, original_price: e.target.value })}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white font-mono focus:outline-none focus:border-obsidian"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-obsidian-700 mb-1">
                    Brand Label
                  </label>
                  <input
                    type="text"
                    value={form.brand_label}
                    onChange={(e) => setForm({ ...form, brand_label: e.target.value })}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-hairline">
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 rounded-xl bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800 transition-colors disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>

          {/* Variants Management */}
          <div className="p-6 bg-ivory-light rounded-2xl border border-hairline space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-obsidian">SKU Variants</h2>
                <p className="text-xs text-obsidian-500">Sizes, colors, and inventory levels.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddVariant(!showAddVariant)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-hairline bg-white text-xs font-medium text-obsidian hover:bg-ivory"
              >
                <Plus className="w-3.5 h-3.5" />
                Add SKU Variant
              </button>
            </div>

            {/* Add Variant Box */}
            {showAddVariant && (
              <form onSubmit={handleCreateVariant} className="p-4 bg-white rounded-xl border border-champagne space-y-3 animate-in fade-in">
                <div className="font-medium text-xs text-obsidian">New Variant Details</div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-[10px] uppercase font-semibold text-obsidian-500 mb-1">SKU *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. UNV-001-XL"
                      value={newVariant.sku}
                      onChange={(e) => setNewVariant({ ...newVariant, sku: e.target.value })}
                      className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-hairline bg-ivory-light font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-semibold text-obsidian-500 mb-1">Size</label>
                    <input
                      type="text"
                      placeholder="S, M, L, XL..."
                      value={newVariant.size}
                      onChange={(e) => setNewVariant({ ...newVariant, size: e.target.value })}
                      className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-hairline bg-ivory-light"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-semibold text-obsidian-500 mb-1">Color Name</label>
                    <input
                      type="text"
                      placeholder="Navy Blue"
                      value={newVariant.color_name}
                      onChange={(e) => setNewVariant({ ...newVariant, color_name: e.target.value })}
                      className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-hairline bg-ivory-light"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-semibold text-obsidian-500 mb-1">Stock Count</label>
                    <input
                      type="number"
                      required
                      value={newVariant.inventory_count}
                      onChange={(e) => setNewVariant({ ...newVariant, inventory_count: Number(e.target.value) })}
                      className="w-full text-xs px-2.5 py-1.5 rounded-lg border border-hairline bg-ivory-light font-mono"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddVariant(false)}
                    className="px-3 py-1 rounded-lg text-xs text-obsidian-500 hover:bg-ivory"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1 rounded-lg bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800"
                  >
                    Add Variant
                  </button>
                </div>
              </form>
            )}

            {/* Variants Table */}
            {variants.length === 0 ? (
              <p className="text-xs text-obsidian-400 py-4 text-center">No variants created yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-hairline text-[10px] uppercase tracking-wider text-obsidian-500 font-semibold">
                      <th className="py-2.5 px-3">SKU</th>
                      <th className="py-2.5 px-3">Size</th>
                      <th className="py-2.5 px-3">Color</th>
                      <th className="py-2.5 px-3">Inventory</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline">
                    {variants.map((v) => (
                      <tr key={v.id || v.sku} className="hover:bg-ivory/50">
                        <td className="py-2.5 px-3 font-mono font-medium text-obsidian">{v.sku}</td>
                        <td className="py-2.5 px-3 font-semibold">{v.size || "-"}</td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-1.5">
                            {v.color_hex && (
                              <span
                                className="w-3.5 h-3.5 rounded-full border border-hairline shadow-2xs inline-block"
                                style={{ backgroundColor: v.color_hex }}
                              />
                            )}
                            <span>{v.color_name || "-"}</span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          <span className={v.inventory_count > 0 ? "text-emerald-700 font-medium" : "text-crimson font-medium"}>
                            {v.inventory_count ?? 0} units
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteVariant(v.id, v.sku)}
                            className="p-1 text-crimson hover:text-crimson/80"
                            title="Delete SKU"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Column (1 col): Status & Product Imagery */}
        <div className="space-y-8">
          {/* Status & Flags Card */}
          <div className="p-6 bg-ivory-light rounded-2xl border border-hairline space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-obsidian">Store Visibility</h2>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-obsidian-700 mb-1">
                  Catalogue Status
                </label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value as any })}
                  className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian font-semibold"
                >
                  <option value="active">Active (Visible on Storefront)</option>
                  <option value="draft">Draft (Admin Only)</option>
                  <option value="archived">Archived (Delisted)</option>
                </select>
              </div>

              <div className="pt-2 space-y-2 border-t border-hairline">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-obsidian font-medium">
                  <input
                    type="checkbox"
                    checked={form.is_new_arrival}
                    onChange={(e) => setForm({ ...form, is_new_arrival: e.target.checked })}
                    className="rounded border-hairline"
                  />
                  Mark as New Arrival
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs text-obsidian font-medium">
                  <input
                    type="checkbox"
                    checked={form.is_featured}
                    onChange={(e) => setForm({ ...form, is_featured: e.target.checked })}
                    className="rounded border-hairline"
                  />
                  Featured in Homepage Curations
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs text-obsidian font-medium">
                  <input
                    type="checkbox"
                    checked={form.is_trending}
                    onChange={(e) => setForm({ ...form, is_trending: e.target.checked })}
                    className="rounded border-hairline"
                  />
                  Highlight in Trending Pieces
                </label>
              </div>
            </div>
          </div>

          {/* Product Media & Image Management */}
          <div className="p-6 bg-ivory-light rounded-2xl border border-hairline space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-obsidian">Product Imagery</h2>
                <p className="text-xs text-obsidian-500">Gallery & primary thumbnail.</p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-ivory border border-hairline">
                {images.length} image(s)
              </span>
            </div>

            {/* Current Images List */}
            {images.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-hairline rounded-xl bg-white/50 space-y-2">
                <ImageIcon className="w-8 h-8 text-obsidian-300 mx-auto" />
                <p className="text-xs text-obsidian-500">No images added yet.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {images.map((img) => (
                  <div
                    key={img.id}
                    className={`relative group rounded-xl overflow-hidden border ${
                      img.is_primary ? "border-champagne-dark ring-2 ring-champagne/40" : "border-hairline"
                    } bg-white shadow-2xs`}
                  >
                    <div className="aspect-3/4 relative bg-ivory-sand/20">
                      <Image
                        src={img.image_url}
                        alt={img.alt_text || form.name}
                        fill
                        className="object-cover"
                        unoptimized
                      />
                    </div>

                    {img.is_primary && (
                      <div className="absolute top-2 left-2 bg-obsidian text-ivory text-[9px] uppercase tracking-wider px-2 py-0.5 rounded font-semibold shadow-xs flex items-center gap-1">
                        <Star className="w-2.5 h-2.5 fill-champagne text-champagne" />
                        Primary
                      </div>
                    )}

                    <div className="p-2 bg-white flex items-center justify-between text-xs border-t border-hairline">
                      {!img.is_primary ? (
                        <button
                          type="button"
                          onClick={() => handleSetPrimaryImage(img.id)}
                          className="text-[10px] text-obsidian-600 hover:text-champagne-dark font-medium"
                        >
                          Set Hero
                        </button>
                      ) : (
                        <span className="text-[10px] text-champagne-dark font-medium">Hero Image</span>
                      )}

                      <button
                        type="button"
                        onClick={() => handleDeleteImage(img.id)}
                        className="p-1 text-crimson hover:text-crimson/80"
                        title="Delete image"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Upload or Add URL Box */}
            <div className="pt-2 border-t border-hairline space-y-3">
              <div className="flex items-center gap-2 border-b border-hairline pb-2 text-xs">
                <button
                  type="button"
                  onClick={() => setUploadTab("url")}
                  className={`pb-1 font-medium transition-colors ${
                    uploadTab === "url"
                      ? "text-obsidian border-b-2 border-obsidian"
                      : "text-obsidian-400 hover:text-obsidian"
                  }`}
                >
                  Add Image URL
                </button>
                <button
                  type="button"
                  onClick={() => setUploadTab("file")}
                  className={`pb-1 font-medium transition-colors ${
                    uploadTab === "file"
                      ? "text-obsidian border-b-2 border-obsidian"
                      : "text-obsidian-400 hover:text-obsidian"
                  }`}
                >
                  Upload File
                </button>
              </div>

              {uploadTab === "url" ? (
                <form onSubmit={handleAddImageUrl} className="space-y-2">
                  <input
                    type="url"
                    required
                    placeholder="https://images.unsplash.com/... or image link"
                    value={newImageUrl}
                    onChange={(e) => setNewImageUrl(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                  />
                  <input
                    type="text"
                    placeholder="Alt text (e.g. Front View)"
                    value={newImageAlt}
                    onChange={(e) => setNewImageAlt(e.target.value)}
                    className="w-full text-xs px-3 py-1.5 rounded-xl border border-hairline bg-white focus:outline-none focus:border-obsidian"
                  />
                  <button
                    type="submit"
                    disabled={uploadingImage}
                    className="w-full py-2 rounded-xl bg-obsidian text-ivory text-xs font-semibold hover:bg-obsidian-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    {uploadingImage ? "Adding..." : "Add Image by URL"}
                  </button>
                </form>
              ) : (
                <div className="space-y-2">
                  <label className="border-2 border-dashed border-hairline rounded-xl p-4 flex flex-col items-center justify-center cursor-pointer hover:border-obsidian transition-colors bg-white/50 text-center">
                    <Upload className="w-6 h-6 text-obsidian-400 mb-1" />
                    <span className="text-xs font-medium text-obsidian">Click to select image file(s)</span>
                    <span className="text-[10px] text-obsidian-400 mt-0.5">Supports multi-image upload (JPEG, PNG, WEBP up to 15MB)</span>
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={handleFileUpload}
                      disabled={uploadingImage}
                      className="hidden"
                    />
                  </label>
                  {uploadingImage && (
                    <p className="text-center text-xs text-obsidian-500 animate-pulse font-mono">
                      Uploading image file...
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
