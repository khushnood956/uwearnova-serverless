/**
 * Create Default Role-Based Accounts for UWEARNOVA
 * - 2 Admin Accounts:
 *     1. admin1@uwearnova.com (Super Admin)
 *     2. admin2@uwearnova.com (Store Admin)
 * - 4 Shop Worker / Staff Accounts:
 *     3. sales1@uwearnova.com (POS Counter Sales & Cashier)
 *     4. sales2@uwearnova.com (Order Fulfillment & Dispatch)
 *     5. inventory1@uwearnova.com (Stock Inward & Warehouse)
 *     6. inventory2@uwearnova.com (Catalog & Product Merchandiser)
 */

const fs = require('fs');
const path = require('path');

const ENV_PATH = path.resolve(__dirname, '../../frontend/.env.local');
const SUPABASE_JS_PATH = path.resolve(__dirname, '../../frontend/node_modules/@supabase/supabase-js');

if (!fs.existsSync(ENV_PATH)) {
  console.error('[ERROR] frontend/.env.local not found.');
  process.exit(1);
}

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
const serviceRoleKey = envVars['SUPABASE_SERVICE_ROLE_KEY'];

if (!supabaseUrl || !serviceRoleKey) {
  console.error('[ERROR] SUPABASE_SERVICE_ROLE_KEY is required to provision auth users.');
  process.exit(1);
}

const { createClient } = require(SUPABASE_JS_PATH);
const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});

const ACCOUNTS = [
  // Admins
  {
    email: 'admin1@uwearnova.com',
    password: 'Admin@UwearNova2026!',
    first_name: 'Lead',
    last_name: 'Administrator',
    role_name: 'super_admin',
    user_type: 'admin',
    title: 'Executive Platform Admin',
    permissions_summary: 'Full platform access, financials, users, settings, and audit logs',
  },
  {
    email: 'admin2@uwearnova.com',
    password: 'Admin@UwearNova2026!',
    first_name: 'Operations',
    last_name: 'Admin',
    role_name: 'store_admin',
    user_type: 'admin',
    title: 'Store Operations Administrator',
    permissions_summary: 'Store settings, reports, staff management, and discounts',
  },
  // Shop Workers / Staff
  {
    email: 'sales1@uwearnova.com',
    password: 'Staff@UwearNova2026!',
    first_name: 'Tariq',
    last_name: 'Cashier',
    role_name: 'pos_cashier',
    user_type: 'staff',
    title: 'POS Counter Sales & Cashier',
    permissions_summary: 'POS counter terminal checkout, cash drawer, and receipt printing',
  },
  {
    email: 'sales2@uwearnova.com',
    password: 'Staff@UwearNova2026!',
    first_name: 'Hamza',
    last_name: 'Fulfillment',
    role_name: 'order_manager',
    user_type: 'staff',
    title: 'Orders & Fulfillment Specialist',
    permissions_summary: 'Order queues, packing, status updates, returns and dispatching',
  },
  {
    email: 'inventory1@uwearnova.com',
    password: 'Staff@UwearNova2026!',
    first_name: 'Bilal',
    last_name: 'Stock',
    role_name: 'inventory_manager',
    user_type: 'staff',
    title: 'Inventory & Warehouse Manager',
    permissions_summary: 'Stock inward receiving, low stock monitoring, and inventory counts',
  },
  {
    email: 'inventory2@uwearnova.com',
    password: 'Staff@UwearNova2026!',
    first_name: 'Zainab',
    last_name: 'Merchandiser',
    role_name: 'catalog_manager',
    user_type: 'staff',
    title: 'Catalog & Media Merchandiser',
    permissions_summary: 'Product creation, R2 media gallery uploads, and price/variant updates',
  },
];

async function provisionAccounts() {
  console.log('================================================================');
  console.log('       PROVISIONING DEFAULT UWEARNOVA ROLE-BASED ACCOUNTS       ');
  console.log('================================================================\n');

  // Fetch available roles
  const { data: roles } = await supabaseAdmin.from('roles').select('id, name');
  const roleMap = new Map((roles || []).map((r) => [r.name, r.id]));

  for (const acc of ACCOUNTS) {
    console.log(`Creating/Syncing: ${acc.email} (${acc.title})...`);

    // 1. Create or Update in Supabase GoTrue Auth
    let authUser = null;
    const { data: createData, error: createErr } = await supabaseAdmin.auth.admin.createUser({
      email: acc.email,
      password: acc.password,
      email_confirm: true,
      user_metadata: {
        first_name: acc.first_name,
        last_name: acc.last_name,
        user_type: acc.user_type,
        role: acc.role_name,
      },
    });

    if (createErr) {
      if (createErr.message.includes('already') || createErr.message.includes('exists')) {
        // User already exists in Auth, fetch and update password
        const { data: listData } = await supabaseAdmin.auth.admin.listUsers();
        authUser = (listData?.users || []).find((u) => u.email === acc.email);
        if (authUser) {
          await supabaseAdmin.auth.admin.updateUserById(authUser.id, {
            password: acc.password,
            email_confirm: true,
            user_metadata: {
              first_name: acc.first_name,
              last_name: acc.last_name,
              user_type: acc.user_type,
              role: acc.role_name,
            },
          });
        }
      } else {
        console.error(`  [ERROR] Auth provisioning failed for ${acc.email}: ${createErr.message}`);
        continue;
      }
    } else {
      authUser = createData.user;
    }

    if (!authUser) {
      console.error(`  [ERROR] Could not resolve Auth user ID for ${acc.email}`);
      continue;
    }

    // 2. Ensure domain user in public.users
    const { data: domainUser, error: userErr } = await supabaseAdmin
      .from('users')
      .upsert(
        {
          auth_user_id: authUser.id,
          email: acc.email,
          user_type: acc.user_type,
          status: 'active',
          email_verified_at: new Date().toISOString(),
        },
        { onConflict: 'email' }
      )
      .select('id')
      .single();

    if (userErr || !domainUser) {
      console.error(`  [ERROR] Domain user sync failed for ${acc.email}: ${userErr?.message}`);
      continue;
    }

    // 3. Map Role in public.user_roles
    const roleId = roleMap.get(acc.role_name);
    if (roleId) {
      await supabaseAdmin.from('user_roles').upsert(
        {
          user_id: domainUser.id,
          role_id: roleId,
        },
        { onConflict: 'user_id,role_id' }
      );
    }

    // 4. Create Staff Profile if user_type is staff or admin
    await supabaseAdmin.from('staff_profiles').upsert(
      {
        user_id: domainUser.id,
        first_name: acc.first_name,
        last_name: acc.last_name,
        job_title: acc.title,
        department: acc.role_name.includes('pos') || acc.role_name.includes('order') ? 'Sales' : acc.role_name.includes('inventory') ? 'Warehouse' : 'Operations',
        is_active: true,
      },
      { onConflict: 'user_id' }
    );

    console.log(`  [SUCCESS] ${acc.email} active with role '${acc.role_name}'`);
  }

  console.log('\n================================================================');
  console.log('ALL DEFAULT ROLE-BASED ACCOUNTS READY FOR TESTING');
  console.log('================================================================');
}

provisionAccounts().catch((err) => {
  console.error(`[FATAL] Provisioning failed: ${err.message}`);
  process.exit(1);
});
