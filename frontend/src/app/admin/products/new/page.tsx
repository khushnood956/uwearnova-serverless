"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Sparkles,
  CheckCircle,
  AlertCircle,
  FolderTree,
  Upload,
  Image as ImageIcon,
  X,
} from "lucide-react";
import { adminApi } from "@/lib/api/admin";
import { CategoryTree } from "@/lib/api/types";

export default function AdminNewProductPage() {
  const router = useRouter();

  // Category Tree State
  const [categories, setCategories] = React.useState<CategoryTree[]>([]);
  const [selectedDeptId, setSelectedDeptId] = React.useState<number | null>(null);
  const [selectedSubcategoryId, setSelectedSubcategoryId] = React.useState<number | null>(null);

  // Inline Subcategory Modal
  const [inlineSubModalOpen, setInlineSubModalOpen] = React.useState(false);
  const [inlineSubName, setInlineSubName] = React.useState("");
  const [inlineSubSlug, setInlineSubSlug] = React.useState("");
  const [inlineSubSaving, setInlineSubSaving] = React.useState(false);

  // Product Form State
  const [form, setForm] = React.useState({
    name: "",
    slug: "",
    subtitle: "",
    description: "",
    imageUrl: "",
    price: "",
    original_price: "",
    brand_label: "UWEARNOVA",
    status: "active" as "draft" | "active" | "archived",
    is_featured: false,
    is_new_arrival: true,
  });

  // Image State
  const [uploadTab, setUploadTab] = React.useState<"file" | "url">("file");
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = React.useState<string>("");
  const [imageUrlInput, setImageUrlInput] = React.useState<string>("");

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const objUrl = URL.createObjectURL(file);
      setPreviewUrl(objUrl);
      setImageUrlInput("");
    }
  };

  const handleUrlChange = (val: string) => {
    setImageUrlInput(val);
    setSelectedFile(null);
    setPreviewUrl(val.trim());
  };

  const handleClearImage = () => {
    setSelectedFile(null);
    setPreviewUrl("");
    setImageUrlInput("");
  };

  // Variants State
  const [variants, setVariants] = React.useState([
    { sku: "UNV-001-S-BLK", size: "S", color_name: "Obsidian Black", color_hex: "#101010", inventory_count: 15 },
    { sku: "UNV-001-M-BLK", size: "M", color_name: "Obsidian Black", color_hex: "#101010", inventory_count: 20 },
    { sku: "UNV-001-L-BLK", size: "L", color_name: "Obsidian Black", color_hex: "#101010", inventory_count: 10 },
  ]);

  const [saving, setSaving] = React.useState(false);
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // Load Categories on Mount
  const loadCategories = React.useCallback(async () => {
    try {
      const tree = await adminApi.getCategoryTree();
      setCategories(tree);
      if (tree.length > 0 && !selectedDeptId) {
        setSelectedDeptId(Number(tree[0].id));
        if (tree[0].children && tree[0].children.length > 0) {
          setSelectedSubcategoryId(Number(tree[0].children[0].id));
        }
      }
    } catch (err: any) {
      showNotification("Failed to load categories: " + err.message, "error");
    }
  }, [selectedDeptId]);

  React.useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  // Available subcategories under selected department
  const currentDept = categories.find((c) => Number(c.id) === selectedDeptId);
  const availableSubcategories = currentDept?.children || [];

  // When department changes, set first subcategory or clear
  const handleDepartmentChange = (deptId: number) => {
    setSelectedDeptId(deptId);
    const dept = categories.find((c) => Number(c.id) === deptId);
    if (dept && dept.children && dept.children.length > 0) {
      setSelectedSubcategoryId(Number(dept.children[0].id));
    } else {
      setSelectedSubcategoryId(null);
    }
  };

  // Auto-fill product slug
  const handleNameChange = (name: string) => {
    const slug = name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-");
    setForm((p) => ({ ...p, name, slug: p.slug ? p.slug : slug }));
  };

  // Auto-fill subcategory slug
  const handleInlineSubNameChange = (name: string) => {
    setInlineSubName(name);
    const prefix = currentDept ? `${currentDept.slug}-` : "";
    const slug = (prefix + name)
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-");
    setInlineSubSlug(slug);
  };

  // Handle INLINE Subcategory Creation (CRITICAL REQUIREMENT)
  const handleCreateInlineSubcategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeptId) {
      showNotification("Please select a parent department first.", "error");
      return;
    }
    setInlineSubSaving(true);
    try {
      // Create subcategory directly via backend category-management API
      const newCategory = await adminApi.createCategory({
        name: inlineSubName,
        slug: inlineSubSlug,
        parent_id: selectedDeptId,
        is_active: true,
        is_coming_soon: false,
      });

      // Refresh category tree
      const updatedTree = await adminApi.getCategoryTree();
      setCategories(updatedTree);

      // Immediately assign and select the newly created subcategory!
      setSelectedSubcategoryId(Number(newCategory.id));
      setInlineSubModalOpen(false);
      setInlineSubName("");
      setInlineSubSlug("");

      showNotification(`Subcategory "${inlineSubName}" created and assigned to product!`);
    } catch (err: any) {
      showNotification(err.message || "Failed to create subcategory", "error");
    } finally {
      setInlineSubSaving(false);
    }
  };

  // Add Variant Row
  const handleAddVariant = () => {
    const skuCode = `UNV-${Math.floor(100 + Math.random() * 900)}-${variants.length + 1}`;
    setVariants((prev) => [
      ...prev,
      { sku: skuCode, size: "M", color_name: "Sand Ivory", color_hex: "#F5F2EB", inventory_count: 10 },
    ]);
  };

  // Remove Variant Row
  const handleRemoveVariant = (index: number) => {
    setVariants((prev) => prev.filter((_, i) => i !== index));
  };

  // Update Variant Row
  const handleUpdateVariant = (index: number, field: string, value: any) => {
    setVariants((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  // Submit Complete Product Form
  const handleSubmitProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetCategoryId = selectedSubcategoryId || selectedDeptId;
    if (!targetCategoryId) {
      showNotification("Please select a department and subcategory.", "error");
      return;
    }
    if (!form.price || isNaN(Number(form.price))) {
      showNotification("Please enter a valid price in PKR.", "error");
      return;
    }
    if (variants.length === 0) {
      showNotification("Please add at least one product SKU variant.", "error");
      return;
    }

    setSaving(true);
    try {
      // 1. Create base product
      const createdProduct = await adminApi.createProduct({
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
      });

      // 2. Create product variants
      for (const v of variants) {
        await adminApi.addVariant(createdProduct.id, {
          sku: v.sku,
          size: v.size,
          color_name: v.color_name,
          color_hex: v.color_hex,
          inventory_count: Number(v.inventory_count),
          is_active: true,
        });
      }

      // 3. Attach image (file upload or URL)
      if (selectedFile) {
        try {
          const fd = new FormData();
          fd.append("file", selectedFile);
          fd.append("alt_text", form.name);
          fd.append("is_primary", "true");
          await adminApi.uploadProductImage(createdProduct.id, fd);
        } catch (imgErr) {
          console.warn("Could not upload image file:", imgErr);
        }
      } else if (imageUrlInput && imageUrlInput.trim()) {
        try {
          await adminApi.addProductImageUrl(createdProduct.id, {
            image_url: imageUrlInput.trim(),
            alt_text: form.name,
            is_primary: true,
          });
        } catch (imgErr) {
          console.warn("Could not attach initial image:", imgErr);
        }
      }

      showNotification(`Product "${form.name}" created with ${variants.length} variant(s)!`);
      setTimeout(() => {
        router.push(`/admin/products/${createdProduct.id}/edit`);
      }, 1000);
    } catch (err: any) {
      showNotification(err.message || "Failed to create product", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Toast */}
      {notification && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-card text-xs font-medium flex items-center gap-2 border animate-in slide-in-from-bottom-2 ${
            notification.type === "success"
              ? "bg-emerald-950 text-emerald-200 border-emerald-800"
              : "bg-crimson text-ivory border-crimson/80"
          }`}
        >
          {notification.type === "success" ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{notification.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between pb-6 border-b border-hairline">
        <div className="space-y-1">
          <Link
            href="/admin/products"
            className="text-xs text-obsidian-500 hover:text-obsidian flex items-center gap-1 font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Products</span>
          </Link>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight">
            Add New Product
          </h1>
          <p className="text-xs text-obsidian-600 font-light">
            Assign dynamic department and subcategory, enter specifications, and configure variants.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmitProduct} className="space-y-8">
        {/* SECTION 1: DYNAMIC CATEGORY ASSIGNMENT WITH INLINE SUBCATEGORY CREATION */}
        <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-hairline">
            <FolderTree className="w-4 h-4 text-champagne-dark" />
            <h2 className="text-xs font-semibold uppercase tracking-wider text-obsidian">
              1. Department & Subcategory Assignment
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
            {/* Department Dropdown */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                Department
              </label>
              <select
                value={selectedDeptId || ""}
                onChange={(e) => handleDepartmentChange(Number(e.target.value))}
                className="w-full px-3 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
                required
              >
                {categories.map((dept) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.name} {dept.is_coming_soon ? "(Coming Soon)" : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Subcategory Dropdown + INLINE CREATE ACTION */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                  Subcategory
                </label>
                {/* INLINE SUB-CATEGORY TRIGGER */}
                <button
                  type="button"
                  onClick={() => {
                    setInlineSubName("");
                    setInlineSubSlug("");
                    setInlineSubModalOpen(true);
                  }}
                  className="text-xs text-champagne-dark hover:underline font-semibold flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>+ New Subcategory</span>
                </button>
              </div>

              <select
                value={selectedSubcategoryId || ""}
                onChange={(e) => setSelectedSubcategoryId(Number(e.target.value))}
                className="w-full px-3 py-2.5 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
                required
              >
                {availableSubcategories.length === 0 ? (
                  <option value="">No subcategories yet — click &ldquo;+ New Subcategory&rdquo;</option>
                ) : (
                  availableSubcategories.map((sub) => (
                    <option key={sub.id} value={sub.id}>
                      {sub.name} (/{sub.slug})
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>
        </div>

        {/* SECTION 2: PRODUCT BASICS */}
        <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-obsidian pb-2 border-b border-hairline">
            2. Piece Details & Narrative
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                Product Title
              </label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="e.g. Sculpted Silk Twill Kurta"
                required
                className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                URL Slug
              </label>
              <input
                type="text"
                value={form.slug}
                onChange={(e) => setForm((p) => ({ ...p, slug: e.target.value }))}
                placeholder="e.g. sculpted-silk-twill-kurta"
                required
                className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory font-mono focus:ring-1 focus:ring-champagne"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                Price (PKR)
              </label>
              <input
                type="number"
                value={form.price}
                onChange={(e) => setForm((p) => ({ ...p, price: e.target.value }))}
                placeholder="14500"
                required
                min={1}
                className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                Compare-at Price (Optional)
              </label>
              <input
                type="number"
                value={form.original_price}
                onChange={(e) => setForm((p) => ({ ...p, original_price: e.target.value }))}
                placeholder="18000"
                className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
                Publication Status
              </label>
              <select
                value={form.status}
                onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as any }))}
                className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory"
              >
                <option value="active">Active (Visible)</option>
                <option value="draft">Draft (Private)</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-obsidian uppercase tracking-wider">
              Description & Craftsmanship Narrative
            </label>
            <textarea
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
              rows={3}
              placeholder="Detailed description of tailoring, fabric weave, and silhouette..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory focus:ring-1 focus:ring-champagne"
            />
          </div>
        </div>

        {/* SECTION 3: PRODUCT IMAGERY */}
        <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-hairline">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-obsidian">
                3. Product Imagery
              </h2>
              <p className="text-[11px] text-obsidian-500 font-light mt-0.5">
                Upload a photo from your computer or enter an image URL to showcase this piece.
              </p>
            </div>
            {previewUrl && (
              <span className="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 font-medium">
                Image Selected
              </span>
            )}
          </div>

          {/* Upload Method Tabs */}
          <div className="flex items-center gap-4 border-b border-hairline pb-2 text-xs">
            <button
              type="button"
              onClick={() => setUploadTab("file")}
              className={`pb-1 font-semibold flex items-center gap-1.5 transition-colors ${
                uploadTab === "file"
                  ? "text-obsidian border-b-2 border-obsidian"
                  : "text-obsidian-400 hover:text-obsidian"
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              Upload Image File
            </button>
            <button
              type="button"
              onClick={() => setUploadTab("url")}
              className={`pb-1 font-semibold flex items-center gap-1.5 transition-colors ${
                uploadTab === "url"
                  ? "text-obsidian border-b-2 border-obsidian"
                  : "text-obsidian-400 hover:text-obsidian"
              }`}
            >
              <ImageIcon className="w-3.5 h-3.5" />
              Enter Image URL
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">
            {/* Input Area */}
            <div>
              {uploadTab === "file" ? (
                <label className="border-2 border-dashed border-hairline hover:border-obsidian transition-colors rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer bg-white text-center">
                  <Upload className="w-8 h-8 text-obsidian-400 mb-2" />
                  <span className="text-xs font-medium text-obsidian">
                    {selectedFile ? selectedFile.name : "Click to select product image file"}
                  </span>
                  <span className="text-[10px] text-obsidian-400 mt-1">
                    Supports JPG, PNG, WEBP (Max 10MB)
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
              ) : (
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-obsidian uppercase tracking-wider block">
                    Public Image URL
                  </label>
                  <input
                    type="url"
                    value={imageUrlInput}
                    onChange={(e) => handleUrlChange(e.target.value)}
                    placeholder="https://images.unsplash.com/... or direct image link"
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-white focus:ring-1 focus:ring-champagne"
                  />
                  <p className="text-[11px] text-obsidian-400">
                    Paste a direct image link from Unsplash, CDN, or your image host.
                  </p>
                </div>
              )}
            </div>

            {/* Preview Area */}
            <div className="border border-hairline rounded-xl p-4 bg-white flex flex-col items-center justify-center min-h-[170px]">
              {previewUrl ? (
                <div className="relative group w-36 aspect-3/4 rounded-lg overflow-hidden border border-champagne shadow-sm">
                  <Image
                    src={previewUrl}
                    alt="Product Preview"
                    fill
                    className="object-cover"
                    unoptimized
                  />
                  <button
                    type="button"
                    onClick={handleClearImage}
                    className="absolute top-1.5 right-1.5 p-1 rounded-full bg-obsidian/80 text-ivory hover:bg-crimson transition-colors"
                    title="Remove image"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                  <div className="absolute bottom-1.5 left-1.5 bg-obsidian/90 text-[9px] text-ivory px-2 py-0.5 rounded font-mono">
                    Primary Photo
                  </div>
                </div>
              ) : (
                <div className="text-center text-obsidian-300 py-6">
                  <ImageIcon className="w-8 h-8 mx-auto mb-1.5 opacity-40" />
                  <p className="text-xs text-obsidian-400">No image selected</p>
                  <p className="text-[10px] text-obsidian-300 mt-0.5">
                    Upload a file or enter a link to preview
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* SECTION 4: VARIANTS, SIZES, COLORS & INVENTORY */}
        <div className="p-6 rounded-2xl bg-ivory-light border border-hairline shadow-subtle space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-hairline">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-obsidian">
              4. Variants, Sizes, Colors & Stock Limits
            </h2>
            <button
              type="button"
              onClick={handleAddVariant}
              className="text-xs text-champagne-dark hover:underline font-semibold flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Variant</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-hairline text-obsidian-500 uppercase tracking-wider text-[10px]">
                  <th className="pb-2 font-semibold">SKU Code</th>
                  <th className="pb-2 font-semibold">Size</th>
                  <th className="pb-2 font-semibold">Color Name</th>
                  <th className="pb-2 font-semibold">Color Hex</th>
                  <th className="pb-2 font-semibold">Inventory Stock</th>
                  <th className="pb-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {variants.map((v, idx) => (
                  <tr key={idx} className="hover:bg-ivory">
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={v.sku}
                        onChange={(e) => handleUpdateVariant(idx, "sku", e.target.value)}
                        className="w-full px-2 py-1 text-xs rounded border border-hairline bg-ivory font-mono"
                        required
                      />
                    </td>
                    <td className="py-2 pr-2 w-24">
                      <select
                        value={v.size}
                        onChange={(e) => handleUpdateVariant(idx, "size", e.target.value)}
                        className="w-full px-2 py-1 text-xs rounded border border-hairline bg-ivory"
                      >
                        <option value="XS">XS</option>
                        <option value="S">S</option>
                        <option value="M">M</option>
                        <option value="L">L</option>
                        <option value="XL">XL</option>
                        <option value="XXL">XXL</option>
                        <option value="One Size">One Size</option>
                      </select>
                    </td>
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        value={v.color_name}
                        onChange={(e) => handleUpdateVariant(idx, "color_name", e.target.value)}
                        className="w-full px-2 py-1 text-xs rounded border border-hairline bg-ivory"
                        required
                      />
                    </td>
                    <td className="py-2 pr-2 w-28">
                      <input
                        type="text"
                        value={v.color_hex}
                        onChange={(e) => handleUpdateVariant(idx, "color_hex", e.target.value)}
                        className="w-full px-2 py-1 text-xs rounded border border-hairline bg-ivory font-mono"
                      />
                    </td>
                    <td className="py-2 pr-2 w-24">
                      <input
                        type="number"
                        min={0}
                        value={v.inventory_count}
                        onChange={(e) => handleUpdateVariant(idx, "inventory_count", Number(e.target.value))}
                        className="w-full px-2 py-1 text-xs rounded border border-hairline bg-ivory font-mono text-center"
                        required
                      />
                    </td>
                    <td className="py-2 text-right">
                      {variants.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveVariant(idx)}
                          className="p-1 text-crimson hover:text-crimson/80"
                          title="Remove variant"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Submit Bar */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-hairline">
          <Link
            href="/admin/products"
            className="px-5 py-2.5 rounded-button border border-hairline text-xs font-semibold text-obsidian hover:bg-ivory-sand transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="px-7 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 disabled:opacity-50 transition-colors"
          >
            {saving ? "Publishing Product..." : "Save & Publish Product"}
          </button>
        </div>
      </form>

      {/* CRITICAL: INLINE SUBCATEGORY CREATION MODAL */}
      {inlineSubModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-md bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4">
            <div>
              <span className="text-[10px] font-semibold tracking-wider uppercase text-champagne-dark">
                Quick Catalogue Architecture
              </span>
              <h3 className="font-serif text-xl font-medium text-obsidian mt-0.5">
                Create & Assign Subcategory
              </h3>
              <p className="text-xs text-obsidian-500 font-light mt-1">
                Add a new line under department <strong>{currentDept?.name}</strong> without leaving this product form.
              </p>
            </div>

            <form onSubmit={handleCreateInlineSubcategory} className="space-y-3">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-obsidian uppercase tracking-wider">
                  Subcategory Name
                </label>
                <input
                  type="text"
                  value={inlineSubName}
                  onChange={(e) => handleInlineSubNameChange(e.target.value)}
                  placeholder="e.g. Jeans & Pants"
                  required
                  autoFocus
                  className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-obsidian uppercase tracking-wider">
                  URL Slug
                </label>
                <input
                  type="text"
                  value={inlineSubSlug}
                  onChange={(e) => setInlineSubSlug(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light font-mono"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setInlineSubModalOpen(false)}
                  className="px-4 py-2 rounded-button text-xs text-obsidian hover:bg-ivory-sand"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inlineSubSaving}
                  className="px-5 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold disabled:opacity-50"
                >
                  {inlineSubSaving ? "Creating..." : "Create & Select"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
