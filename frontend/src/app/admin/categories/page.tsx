"use client";

import * as React from "react";
import {
  FolderTree,
  Plus,
  Edit2,
  Trash2,
  Eye,
  EyeOff,
  Sparkles,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  ArrowUpDown,
  RefreshCw,
} from "lucide-react";
import { adminApi, AdminCategoryCreate, AdminCategoryUpdate } from "@/lib/api/admin";
import { CategoryTree } from "@/lib/api/types";

export default function AdminCategoriesPage() {
  const [tree, setTree] = React.useState<CategoryTree[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [expandedDepts, setExpandedDepts] = React.useState<Record<string, boolean>>({});
  const [notification, setNotification] = React.useState<{ text: string; type: "success" | "error" } | null>(null);

  // Modal State
  const [modalOpen, setModalOpen] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);
  const [editingId, setEditingId] = React.useState<string | number | null>(null);

  const [formData, setFormData] = React.useState<{
    name: string;
    slug: string;
    description: string;
    parent_id: number | null;
    sort_order: number;
    is_active: boolean;
    is_coming_soon: boolean;
  }>({
    name: "",
    slug: "",
    description: "",
    parent_id: null,
    sort_order: 0,
    is_active: true,
    is_coming_soon: false,
  });

  const showNotification = (text: string, type: "success" | "error" = "success") => {
    setNotification({ text, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadTree = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.getCategoryTree();
      setTree(data);
      // Expand all by default
      const exp: Record<string, boolean> = {};
      data.forEach((d) => {
        exp[String(d.id)] = true;
      });
      setExpandedDepts(exp);
    } catch (err: any) {
      showNotification(err.message || "Failed to load category tree", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadTree();
  }, [loadTree]);

  const toggleExpand = (id: string | number) => {
    setExpandedDepts((prev) => ({
      ...prev,
      [String(id)]: !prev[String(id)],
    }));
  };

  // Open modal for new Department
  const handleOpenNewDept = () => {
    setIsEditing(false);
    setEditingId(null);
    setFormData({
      name: "",
      slug: "",
      description: "",
      parent_id: null,
      sort_order: tree.length + 1,
      is_active: true,
      is_coming_soon: false,
    });
    setModalOpen(true);
  };

  // Open modal for new Subcategory under parent
  const handleOpenNewSubcategory = (parentId: number | string) => {
    setIsEditing(false);
    setEditingId(null);
    setFormData({
      name: "",
      slug: "",
      description: "",
      parent_id: Number(parentId),
      sort_order: 0,
      is_active: true,
      is_coming_soon: false,
    });
    setModalOpen(true);
  };

  // Open modal for editing
  const handleOpenEdit = (item: CategoryTree) => {
    setIsEditing(true);
    setEditingId(item.id);
    setFormData({
      name: item.name,
      slug: item.slug,
      description: item.description || "",
      parent_id: item.parent_id ? Number(item.parent_id) : null,
      sort_order: item.sort_order ?? item.display_order ?? 0,
      is_active: Boolean(item.is_active),
      is_coming_soon: Boolean(item.is_coming_soon),
    });
    setModalOpen(true);
  };

  // Handle Form Submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditing && editingId) {
        await adminApi.updateCategory(editingId, {
          name: formData.name,
          slug: formData.slug,
          description: formData.description || undefined,
          parent_id: formData.parent_id,
          sort_order: formData.sort_order,
          is_active: formData.is_active,
          is_coming_soon: formData.is_coming_soon,
        });
        showNotification(`Category "${formData.name}" updated successfully.`);
      } else {
        await adminApi.createCategory({
          name: formData.name,
          slug: formData.slug,
          description: formData.description || undefined,
          parent_id: formData.parent_id,
          sort_order: formData.sort_order,
          is_active: formData.is_active,
          is_coming_soon: formData.is_coming_soon,
        });
        showNotification(
          formData.parent_id
            ? `Subcategory "${formData.name}" created.`
            : `Department "${formData.name}" created.`
        );
      }
      setModalOpen(false);
      await loadTree();
    } catch (err: any) {
      showNotification(err.message || "Failed to save category", "error");
    }
  };

  // Toggle Coming Soon status
  const handleToggleComingSoon = async (item: CategoryTree) => {
    try {
      await adminApi.updateCategory(item.id, {
        is_coming_soon: !item.is_coming_soon,
      });
      showNotification(
        `"${item.name}" is now ${!item.is_coming_soon ? "marked Coming Soon" : "activated for shopping"}.`
      );
      await loadTree();
    } catch (err: any) {
      showNotification(err.message || "Failed to toggle coming soon status", "error");
    }
  };

  // Toggle Active/Inactive
  const handleToggleActive = async (item: CategoryTree) => {
    try {
      await adminApi.updateCategory(item.id, {
        is_active: !item.is_active,
      });
      showNotification(
        `"${item.name}" ${!item.is_active ? "is now active" : "is now hidden"}.`
      );
      await loadTree();
    } catch (err: any) {
      showNotification(err.message || "Failed to toggle active status", "error");
    }
  };

  // Delete Category
  const handleDelete = async (item: CategoryTree) => {
    const isDept = !item.parent_id;
    const msg = isDept
      ? `Are you sure you want to delete department "${item.name}"? Subcategories and assigned products must be reassigned first.`
      : `Are you sure you want to delete subcategory "${item.name}"?`;

    if (!confirm(msg)) return;

    try {
      await adminApi.deleteCategory(item.id);
      showNotification(`Category "${item.name}" deleted.`);
      await loadTree();
    } catch (err: any) {
      showNotification(err.message || "Cannot delete category with active products/subcategories", "error");
    }
  };

  // Auto-generate slug from name
  const handleNameChange = (val: string) => {
    const slug = val
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-");
    setFormData((p) => ({ ...p, name: val, slug: p.slug && isEditing ? p.slug : slug }));
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Toast Notification */}
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-hairline">
        <div>
          <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-champagne-dark">
            Catalogue Architecture
          </span>
          <h1 className="font-serif text-3xl font-medium text-obsidian tracking-tight mt-1">
            Department & Category Hierarchy
          </h1>
          <p className="text-xs sm:text-sm text-obsidian-600 mt-1 font-light">
            Manage top-level store departments (Men, Women, Kids), Coming Soon states (Footwear, Accessories, Perfumes), and flexible subcategories.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadTree}
            disabled={loading}
            className="p-2.5 rounded-button border border-hairline text-obsidian hover:bg-ivory-sand disabled:opacity-50 transition-colors"
            title="Refresh tree"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <button
            type="button"
            onClick={handleOpenNewDept}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-button bg-obsidian text-ivory text-xs font-semibold uppercase tracking-wider hover:bg-obsidian-800 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create Department</span>
          </button>
        </div>
      </div>

      {/* Hierarchy Tree Card */}
      <div className="bg-ivory-light rounded-2xl border border-hairline shadow-subtle overflow-hidden">
        <div className="p-4 bg-ivory-sand/50 border-b border-hairline flex items-center justify-between text-xs font-semibold text-obsidian-600 uppercase tracking-wider">
          <div className="flex items-center gap-2">
            <FolderTree className="w-4 h-4 text-champagne-dark" />
            <span>Departments & Subcategories</span>
          </div>
          <span>Status & Operational Controls</span>
        </div>

        {loading ? (
          <div className="py-20 text-center">
            <div className="w-7 h-7 border-2 border-champagne border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs text-obsidian-500">Loading catalogue architecture...</p>
          </div>
        ) : tree.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <p className="text-sm font-medium text-obsidian">No categories found</p>
            <button
              type="button"
              onClick={handleOpenNewDept}
              className="text-xs text-champagne-dark font-medium underline"
            >
              Add initial department (e.g. Men)
            </button>
          </div>
        ) : (
          <div className="divide-y divide-hairline">
            {tree.map((dept) => {
              const hasChildren = dept.children && dept.children.length > 0;
              const isExpanded = expandedDepts[String(dept.id)] ?? true;

              return (
                <div key={dept.id} className="bg-ivory transition-colors">
                  {/* Department Row */}
                  <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-ivory-sand/30">
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => toggleExpand(dept.id)}
                        className="p-1 rounded text-obsidian-400 hover:text-obsidian"
                      >
                        {hasChildren ? (
                          isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                        ) : (
                          <span className="w-4 h-4 inline-block" />
                        )}
                      </button>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-serif text-base font-semibold text-obsidian">{dept.name}</span>
                          <span className="text-[11px] font-mono text-obsidian-400">/{dept.slug}</span>

                          {dept.is_coming_soon ? (
                            <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-champagne-light text-champagne-dark border border-champagne-dark/20">
                              Coming Soon
                            </span>
                          ) : (
                            <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Active Shopping
                            </span>
                          )}

                          {!dept.is_active && (
                            <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-crimson/10 text-crimson">
                              Hidden
                            </span>
                          )}
                        </div>

                        {dept.description && (
                          <p className="text-xs text-obsidian-500 font-light mt-0.5">{dept.description}</p>
                        )}
                      </div>
                    </div>

                    {/* Department Control Buttons */}
                    <div className="flex items-center gap-2 self-start md:self-auto pl-7 md:pl-0">
                      {/* Toggle Coming Soon */}
                      <button
                        type="button"
                        onClick={() => handleToggleComingSoon(dept)}
                        className={`text-xs px-2.5 py-1.5 rounded-button font-medium border transition-colors ${
                          dept.is_coming_soon
                            ? "border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100"
                            : "border-champagne-dark/30 text-champagne-dark bg-champagne-light/50 hover:bg-champagne-light"
                        }`}
                        title={dept.is_coming_soon ? "Activate this department for shopping" : "Mark department as Coming Soon"}
                      >
                        {dept.is_coming_soon ? "Activate Dept" : "Mark Coming Soon"}
                      </button>

                      {/* Add Subcategory Button */}
                      <button
                        type="button"
                        onClick={() => handleOpenNewSubcategory(dept.id)}
                        className="text-xs px-2.5 py-1.5 rounded-button font-medium border border-hairline text-obsidian hover:bg-ivory-sand flex items-center gap-1"
                        title="Add subcategory under this department"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Sub</span>
                      </button>

                      {/* Visibility Toggle */}
                      <button
                        type="button"
                        onClick={() => handleToggleActive(dept)}
                        className="p-1.5 rounded text-obsidian-500 hover:text-obsidian"
                        title={dept.is_active ? "Hide from navigation" : "Show in navigation"}
                      >
                        {dept.is_active ? <Eye className="w-4 h-4 text-emerald-600" /> : <EyeOff className="w-4 h-4 text-obsidian-400" />}
                      </button>

                      {/* Edit */}
                      <button
                        type="button"
                        onClick={() => handleOpenEdit(dept)}
                        className="p-1.5 rounded text-obsidian-500 hover:text-obsidian"
                        title="Edit department"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>

                      {/* Delete */}
                      <button
                        type="button"
                        onClick={() => handleDelete(dept)}
                        className="p-1.5 rounded text-crimson hover:text-crimson/80"
                        title="Delete department"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Subcategories Children */}
                  {hasChildren && isExpanded && (
                    <div className="bg-ivory-light/60 pl-10 pr-4 py-2 border-t border-hairline/60 divide-y divide-hairline/40">
                      {dept.children.map((sub) => (
                        <div
                          key={sub.id}
                          className="py-2.5 flex items-center justify-between gap-3 text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-obsidian">{sub.name}</span>
                            <span className="font-mono text-obsidian-400 text-[11px]">/{sub.slug}</span>
                            {!sub.is_active && (
                              <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-crimson/10 text-crimson font-medium">
                                Inactive
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleToggleActive(sub)}
                              className="p-1 text-obsidian-400 hover:text-obsidian"
                              title={sub.is_active ? "Deactivate" : "Activate"}
                            >
                              {sub.is_active ? <Eye className="w-3.5 h-3.5 text-emerald-600" /> : <EyeOff className="w-3.5 h-3.5" />}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleOpenEdit(sub)}
                              className="p-1 text-obsidian-400 hover:text-obsidian"
                              title="Edit subcategory"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDelete(sub)}
                              className="p-1 text-crimson hover:text-crimson/80"
                              title="Delete subcategory"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Category Create/Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian/60 backdrop-blur-xs">
          <div className="w-full max-w-lg bg-ivory rounded-2xl p-6 shadow-card border border-hairline space-y-4">
            <h3 className="font-serif text-xl font-medium text-obsidian">
              {isEditing
                ? `Edit ${formData.parent_id ? "Subcategory" : "Department"}`
                : formData.parent_id
                ? "Create New Subcategory"
                : "Create New Department"}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Parent Department Selection */}
              {formData.parent_id !== null && (
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase tracking-wider">
                    Parent Department
                  </label>
                  <select
                    value={formData.parent_id || ""}
                    onChange={(e) => setFormData((p) => ({ ...p, parent_id: Number(e.target.value) }))}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                    required
                  >
                    {tree.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.slug})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase tracking-wider">
                    Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    placeholder="e.g. Hoodies or Footwear"
                    required
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase tracking-wider">
                    URL Slug
                  </label>
                  <input
                    type="text"
                    value={formData.slug}
                    onChange={(e) => setFormData((p) => ({ ...p, slug: e.target.value }))}
                    placeholder="e.g. men-hoodies"
                    required
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light font-mono"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-obsidian uppercase tracking-wider">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
                  rows={2}
                  placeholder="Curated description for storefront hero..."
                  className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                />
              </div>

              <div className="grid grid-cols-3 gap-3 pt-2">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-obsidian uppercase tracking-wider">
                    Display Order
                  </label>
                  <input
                    type="number"
                    value={formData.sort_order}
                    onChange={(e) => setFormData((p) => ({ ...p, sort_order: Number(e.target.value) }))}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-hairline bg-ivory-light"
                  />
                </div>

                <div className="flex items-center gap-2 pt-5">
                  <input
                    type="checkbox"
                    id="is_active_cat"
                    checked={formData.is_active}
                    onChange={(e) => setFormData((p) => ({ ...p, is_active: e.target.checked }))}
                    className="rounded border-hairline text-champagne-dark"
                  />
                  <label htmlFor="is_active_cat" className="text-xs text-obsidian">
                    Active & Visible
                  </label>
                </div>

                {formData.parent_id === null && (
                  <div className="flex items-center gap-2 pt-5">
                    <input
                      type="checkbox"
                      id="is_coming_soon_cat"
                      checked={formData.is_coming_soon}
                      onChange={(e) => setFormData((p) => ({ ...p, is_coming_soon: e.target.checked }))}
                      className="rounded border-hairline text-champagne-dark"
                    />
                    <label htmlFor="is_coming_soon_cat" className="text-xs text-champagne-dark font-medium">
                      Coming Soon
                    </label>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-hairline">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-button text-xs text-obsidian hover:bg-ivory-sand"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-button bg-obsidian text-ivory text-xs font-semibold"
                >
                  {isEditing ? "Save Changes" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
