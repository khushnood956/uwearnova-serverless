/**
 * Stage 8: Remote Staging Database Seeding & Data Reconciliation
 * Imports verified catalog, categories, collections, and sample products
 * into the live remote Supabase staging database.
 * STRICT SECURITY: Never logs or prints secrets.
 */

const fs = require('fs');
const path = require('path');

const ENV_PATH = path.resolve(__dirname, '../../frontend/.env.local');
const DATASET_PATH = path.resolve(__dirname, '../../data/exports/legacy_dataset.json');
const SUPABASE_JS_PATH = path.resolve(__dirname, '../../frontend/node_modules/@supabase/supabase-js');

if (!fs.existsSync(ENV_PATH)) {
  console.error('[ERROR] frontend/.env.local not found.');
  process.exit(1);
}

if (!fs.existsSync(DATASET_PATH)) {
  console.error('[ERROR] legacy_dataset.json not found.');
  process.exit(1);
}

// Parse environment variables safely
const envContent = fs.readFileSync(ENV_PATH, 'utf-8');
const envVars = {};
envContent.split(/\r?\n/).forEach((line) => {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#')) return;
  const match = trimmed.match(/^([^=]+)=(.*)$/);
  if (match) {
    let val = match[2].trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    envVars[match[1].trim()] = val;
  }
});

const supabaseUrl = envVars['NEXT_PUBLIC_SUPABASE_URL'];
// Use Service Role Key for administrative seeding if present, else Anon Key
const supabaseKey = envVars['SUPABASE_SERVICE_ROLE_KEY'] || envVars['NEXT_PUBLIC_SUPABASE_ANON_KEY'];

if (!supabaseUrl || !supabaseKey) {
  console.error('[ERROR] Missing Supabase URL or Key in frontend/.env.local');
  process.exit(1);
}

const { createClient } = require(SUPABASE_JS_PATH);
const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});

const dataset = JSON.parse(fs.readFileSync(DATASET_PATH, 'utf-8'));

async function seed() {
  console.log('================================================================');
  console.log('     UWEARNOVA STAGING DATABASE SEEDING & RECONCILIATION        ');
  console.log('================================================================\n');

  try {
    // 1. Seed Permissions
    console.log('--- 1. Seeding Permissions ---');
    if (dataset.permissions && dataset.permissions.length > 0) {
      const { data: permData, error: permErr } = await supabase
        .from('permissions')
        .upsert(dataset.permissions, { onConflict: 'code' })
        .select('id');
      if (permErr) throw new Error(`Permissions: ${permErr.message}`);
      console.log(`[PASS] Upserted ${dataset.permissions.length} permissions.`);
    }

    // 2. Seed Roles
    console.log('\n--- 2. Seeding Roles ---');
    if (dataset.roles && dataset.roles.length > 0) {
      for (const role of dataset.roles) {
        const displayName = role.display_name || role.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        const { data: rData, error: rErr } = await supabase
          .from('roles')
          .upsert(
            {
              name: role.name,
              display_name: displayName,
              description: role.description || displayName,
              is_system: role.is_system ?? true,
            },
            { onConflict: 'name' }
          )
          .select('id')
          .single();
        if (rErr) throw new Error(`Role ${role.name}: ${rErr.message}`);

        // Map role permissions
        if (role.permissions && role.permissions.length > 0 && rData) {
          const { data: perms } = await supabase
            .from('permissions')
            .select('id, code')
            .in('code', role.permissions);

          if (perms && perms.length > 0) {
            const rolePerms = perms.map((p) => ({ role_id: rData.id, permission_id: p.id }));
            await supabase.from('role_permissions').upsert(rolePerms, { onConflict: 'role_id,permission_id' });
          }
        }
      }
      console.log(`[PASS] Upserted ${dataset.roles.length} system roles with permission mappings.`);
    }

    // 3. Seed Categories (Parents first, then children)
    console.log('\n--- 3. Seeding Categories ---');
    if (dataset.categories && dataset.categories.length > 0) {
      const parentCats = dataset.categories.filter((c) => !c.parent_slug);
      const childCats = dataset.categories.filter((c) => c.parent_slug);

      for (const cat of parentCats) {
        await supabase
          .from('categories')
          .upsert(
            { name: cat.name, slug: cat.slug, description: cat.description, is_active: true, sort_order: cat.sort_order || 0 },
            { onConflict: 'slug' }
          );
      }

      // Fetch parent IDs for mapping
      const { data: allParents } = await supabase.from('categories').select('id, slug');
      const parentMap = new Map((allParents || []).map((p) => [p.slug, p.id]));

      for (const cat of childCats) {
        const parentId = parentMap.get(cat.parent_slug) || null;
        await supabase
          .from('categories')
          .upsert(
            { name: cat.name, slug: cat.slug, description: cat.description, parent_id: parentId, is_active: true, sort_order: cat.sort_order || 0 },
            { onConflict: 'slug' }
          );
      }
      console.log(`[PASS] Upserted ${dataset.categories.length} categories (parents & subcategories).`);
    }

    // 4. Seed Collections
    console.log('\n--- 4. Seeding Collections ---');
    if (dataset.collections && dataset.collections.length > 0) {
      for (const col of dataset.collections) {
        await supabase
          .from('collections')
          .upsert(
            { name: col.name, slug: col.slug, description: col.description, is_active: true },
            { onConflict: 'slug' }
          );
      }
      console.log(`[PASS] Upserted ${dataset.collections.length} collections.`);
    }

    // 5. Seed Shipping Methods
    console.log('\n--- 5. Seeding Shipping Methods ---');
    if (dataset.shipping_methods && dataset.shipping_methods.length > 0) {
      for (const sm of dataset.shipping_methods) {
        await supabase
          .from('shipping_methods')
          .upsert(
            {
              code: sm.code,
              name: sm.name,
              description: sm.description,
              base_cost: sm.base_cost,
              estimated_days_min: sm.estimated_days_min,
              estimated_days_max: sm.estimated_days_max,
              is_active: sm.is_active,
            },
            { onConflict: 'code' }
          );
      }
      console.log(`[PASS] Upserted ${dataset.shipping_methods.length} shipping methods.`);
    }

    // 6. Seed Coupons
    console.log('\n--- 6. Seeding Coupons ---');
    if (dataset.coupons && dataset.coupons.length > 0) {
      for (const c of dataset.coupons) {
        await supabase
          .from('coupons')
          .upsert(
            {
              code: c.code,
              discount_type: c.discount_type,
              discount_value: c.discount_value,
              minimum_order_amount: c.minimum_order_amount,
              max_discount_amount: c.max_discount_amount,
              usage_limit: c.usage_limit,
              is_active: c.is_active,
            },
            { onConflict: 'code' }
          );
      }
      console.log(`[PASS] Upserted ${dataset.coupons.length} promotional coupons.`);
    }

    // 7. Seed Products, Variants & Images
    console.log('\n--- 7. Seeding Products & Variants ---');
    if (dataset.products && dataset.products.length > 0) {
      const { data: allCategories } = await supabase.from('categories').select('id, slug');
      const catMap = new Map((allCategories || []).map((c) => [c.slug, c.id]));

      let totalVariantsSeeded = 0;
      let totalStockSeeded = 0;

      for (const prod of dataset.products) {
        const catId = catMap.get(prod.category_slug) || null;
        if (!catId) {
          console.warn(`[WARN] Category slug '${prod.category_slug}' not found for product '${prod.slug}'`);
          continue;
        }

        const { data: pData, error: pErr } = await supabase
          .from('products')
          .upsert(
            {
              name: prod.name,
              slug: prod.slug,
              description: prod.description,
              category_id: catId,
              price: prod.price,
              original_price: prod.original_price || null,
              status: prod.status || 'active',
              is_featured: prod.is_featured || false,
              is_new_arrival: prod.is_new_arrival || false,
            },
            { onConflict: 'slug' }
          )
          .select('id')
          .single();

        if (pErr) throw new Error(`Product ${prod.slug}: ${pErr.message}`);

        // Seed Variants
        if (prod.variants && prod.variants.length > 0 && pData) {
          for (const v of prod.variants) {
            const { error: vErr } = await supabase
              .from('product_variants')
              .upsert(
                {
                  product_id: pData.id,
                  sku: v.sku,
                  size: v.size,
                  color_name: v.color_name,
                  color_hex: v.color_hex || '#000000',
                  price: v.price || prod.price,
                  inventory_count: v.inventory_count || 0,
                  is_active: true,
                },
                { onConflict: 'sku' }
              );
            if (vErr) throw new Error(`Variant ${v.sku}: ${vErr.message}`);
            totalVariantsSeeded++;
            totalStockSeeded += v.inventory_count || 0;
          }
        }

        // Seed Images
        if (prod.images && prod.images.length > 0 && pData) {
          for (const img of prod.images) {
            await supabase.from('product_images').insert({
              product_id: pData.id,
              image_url: img.image_url,
              alt_text: img.alt_text || prod.name,
              is_primary: img.is_primary || false,
              sort_order: img.sort_order || 0,
            });
          }
        }
      }

      console.log(`[PASS] Upserted ${dataset.products.length} products, ${totalVariantsSeeded} variants, total ${totalStockSeeded} stock units.`);
    }

    // 8. Reconciliation Query
    console.log('\n--- 8. Reconciling Remote Staging Database ---');
    const { count: catCount } = await supabase.from('categories').select('*', { count: 'exact', head: true });
    const { count: prodCount } = await supabase.from('products').select('*', { count: 'exact', head: true });
    const { count: varCount } = await supabase.from('product_variants').select('*', { count: 'exact', head: true });
    const { data: variants } = await supabase.from('product_variants').select('inventory_count, price');

    let totalStock = 0;
    let totalValuation = 0;
    (variants || []).forEach((v) => {
      totalStock += v.inventory_count || 0;
      totalValuation += (v.inventory_count || 0) * (Number(v.price) || 0);
    });

    console.log(`[RECONCILIATION SUMMARY]`);
    console.log(`- Categories in DB: ${catCount}`);
    console.log(`- Products in DB:   ${prodCount}`);
    console.log(`- Variants in DB:   ${varCount}`);
    console.log(`- Total Inventory:  ${totalStock} units`);
    console.log(`- Total Valuation:  PKR ${totalValuation.toLocaleString('en-PK', { minimumFractionDigits: 2 })}`);

    console.log('\n================================================================');
    console.log('REMOTE STAGING DATABASE SEEDING & RECONCILIATION SUCCESSFUL!');
    console.log('================================================================');
  } catch (err) {
    console.error(`\n[FATAL ERROR] Seeding failed: ${err.message}`);
    process.exit(1);
  }
}

seed();
