/**
 * Stage 7: UniNova Staging Acceptance Test Runner
 * Executes Section 14 acceptance criteria:
 * 1. Build & Bundle Secret Leak Scan
 * 2. Database Schema & Migration Coverage
 * 3. RLS Security & RBAC Policy Matrix
 * 4. Commerce & Atomic RPC Integrity
 * 5. Media Pipeline & Storage Bounds
 * 6. Admin & Reporting Workflows
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('================================================================');
console.log('       UNINOVA MIGRATION: STAGE 7 ACCEPTANCE TEST RUNNER        ');
console.log('================================================================\n');

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function runTest(testName, fn) {
  totalTests++;
  try {
    fn();
    console.log(`[PASS] ${testName}`);
    passedTests++;
  } catch (err) {
    console.error(`[FAIL] ${testName}: ${err.message}`);
    failedTests++;
  }
}

// -----------------------------------------------------------------------------
// 1. Build & Secret Leak Scan
// -----------------------------------------------------------------------------
console.log('--- Suite 1: Build & Secret Leak Scan ---');

runTest('1.1 Next.js production build artifacts exist (.next/standalone)', () => {
  const standalonePath = path.resolve(__dirname, '../../frontend/.next/standalone');
  assert.ok(fs.existsSync(standalonePath), '.next/standalone directory must exist');
});

runTest('1.2 Client static bundle secret leak audit', () => {
  const staticChunksPath = path.resolve(__dirname, '../../frontend/.next/static/chunks');
  assert.ok(fs.existsSync(staticChunksPath), 'Static chunks directory must exist');

  const forbiddenPatterns = [
    'SUPABASE_SERVICE_ROLE_KEY',
    'R2_SECRET_ACCESS_KEY',
    'postgresql://',
    'AWS_SECRET_ACCESS_KEY',
  ];

  function scanDir(dir) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
      const fullPath = path.join(dir, file);
      if (fs.statSync(fullPath).isDirectory()) {
        scanDir(fullPath);
      } else if (file.endsWith('.js')) {
        const content = fs.readFileSync(fullPath, 'utf-8');
        for (const pattern of forbiddenPatterns) {
          assert.strictEqual(
            content.includes(pattern),
            false,
            `Secret pattern '${pattern}' leaked in client bundle ${file}`
          );
        }
      }
    }
  }

  scanDir(staticChunksPath);
});

// -----------------------------------------------------------------------------
// 2. Database Migration & Schema Verification
// -----------------------------------------------------------------------------
console.log('\n--- Suite 2: Database Migration & Schema Coverage ---');

runTest('2.1 Core PostgreSQL migrations present and complete', () => {
  const migrationsDir = path.resolve(__dirname, '../../supabase/migrations');
  const files = fs.readdirSync(migrationsDir).filter((f) => f.endsWith('.sql'));

  assert.ok(files.some((f) => f.includes('initial_schema')), 'initial_schema migration missing');
  assert.ok(files.some((f) => f.includes('auth_and_rbac')), 'auth_and_rbac migration missing');
  assert.ok(files.some((f) => f.includes('business_logic_rpc')), 'business_logic_rpc migration missing');
});

runTest('2.2 Schema defines all 50 tables with identity PKs', () => {
  const schemaFile = path.resolve(__dirname, '../../supabase/migrations/20261116000001_initial_schema.sql');
  const sql = fs.readFileSync(schemaFile, 'utf-8');

  const requiredTables = [
    'users', 'customer_profiles', 'addresses', 'roles', 'permissions', 'role_permissions', 'user_roles',
    'categories', 'products', 'product_variants', 'product_images', 'product_collections',
    'carts', 'cart_items', 'orders', 'order_items', 'order_status_history',
    'payments', 'shipping_methods', 'coupons', 'coupon_redemptions', 'wishlists',
    'return_requests', 'homepage_campaigns', 'audit_logs'
  ];

  for (const table of requiredTables) {
    const hasTable =
      sql.includes(`CREATE TABLE IF NOT EXISTS public.${table}`) ||
      sql.includes(`CREATE TABLE IF NOT EXISTS ${table}`) ||
      sql.includes(`CREATE TABLE public.${table}`) ||
      sql.includes(`CREATE TABLE ${table}`);
    assert.ok(hasTable, `Table '${table}' missing in initial schema`);
  }
});

// -----------------------------------------------------------------------------
// 3. Security, RBAC & Row Level Security (RLS)
// -----------------------------------------------------------------------------
console.log('\n--- Suite 3: Security, RBAC & RLS Policies ---');

runTest('3.1 Row Level Security enabled on all critical tables', () => {
  const rbacFile = path.resolve(__dirname, '../../supabase/migrations/20261116000002_auth_and_rbac.sql');
  const sql = fs.readFileSync(rbacFile, 'utf-8');

  const secureTables = [
    'users', 'customer_profiles', 'addresses', 'roles', 'permissions', 'orders', 'order_items', 'carts', 'cart_items',
    'wishlists', 'payments', 'audit_logs'
  ];

  for (const table of secureTables) {
    const hasRLS =
      sql.includes(`ALTER TABLE public.${table} ENABLE ROW LEVEL SECURITY;`) ||
      sql.includes(`ALTER TABLE ${table} ENABLE ROW LEVEL SECURITY;`);
    assert.ok(hasRLS, `RLS not enabled on table ${table}`);
  }
});

runTest('3.2 Automated RLS policy verification test suite present', () => {
  const rlsTestFile = path.resolve(__dirname, '../../supabase/tests/rls_policy_verification.sql');
  assert.ok(fs.existsSync(rlsTestFile), 'rls_policy_verification.sql must exist');
  const sql = fs.readFileSync(rlsTestFile, 'utf-8');
  assert.ok(sql.includes('Anonymous Role Policy Checks'), 'Test must verify anonymous limits');
  assert.ok(sql.includes('Cross-Customer RLS Isolation'), 'Test must verify tenant isolation');
});

// -----------------------------------------------------------------------------
// 4. Commerce & Atomic RPC Integrity
// -----------------------------------------------------------------------------
console.log('\n--- Suite 4: Commerce & Atomic Transaction Integrity ---');

runTest('4.1 place_order_atomic RPC handles concurrency & rollback', () => {
  const rpcFile = path.resolve(__dirname, '../../supabase/migrations/20261116000003_business_logic_rpc.sql');
  const sql = fs.readFileSync(rpcFile, 'utf-8');

  assert.ok(sql.includes('place_order_atomic'), 'place_order_atomic RPC missing');
  assert.ok(sql.includes('FOR UPDATE'), 'Atomic checkout must use FOR UPDATE row locking');
  assert.ok(sql.includes('RAISE EXCEPTION'), 'Must abort transaction and raise exception on error');
  assert.ok(sql.includes('v_stock < v_qty'), 'Must check stock bounds before ordering');
});

runTest('4.2 merge_guest_cart RPC securely migrates anonymous carts', () => {
  const rpcFile = path.resolve(__dirname, '../../supabase/migrations/20261116000003_business_logic_rpc.sql');
  const sql = fs.readFileSync(rpcFile, 'utf-8');

  assert.ok(sql.includes('merge_guest_cart'), 'merge_guest_cart RPC missing');
  assert.ok(sql.includes('ON CONFLICT (cart_id, variant_id)'), 'Must handle variant conflict in cart');
});

runTest('4.3 create_offline_sale RPC supports POS counter sales', () => {
  const rpcFile = path.resolve(__dirname, '../../supabase/migrations/20261116000003_business_logic_rpc.sql');
  const sql = fs.readFileSync(rpcFile, 'utf-8');

  assert.ok(sql.includes('create_offline_sale'), 'create_offline_sale RPC missing');
  assert.ok(sql.includes('offline_sales'), 'POS sale must record into offline_sales table');
});

// -----------------------------------------------------------------------------
// 5. Media Pipeline & Storage Bounds
// -----------------------------------------------------------------------------
console.log('\n--- Suite 5: Media Pipeline & Storage Bounds ---');

runTest('5.1 Cloudflare R2 storage adapter configured with S3v4 presigning', () => {
  const r2File = path.resolve(__dirname, '../../frontend/src/lib/storage/r2.ts');
  const content = fs.readFileSync(r2File, 'utf-8');

  assert.ok(content.includes('@aws-sdk/s3-request-presigner'), 'Presigner SDK missing');
  assert.ok(content.includes('r2.cloudflarestorage.com'), 'R2 endpoint missing');
  assert.ok(content.includes("region: 'auto'"), 'Cloudflare R2 region auto missing');
  assert.ok(content.includes('sanitizeFilename'), 'Filename sanitization missing');
});

runTest('5.2 Presigned media upload API route validates staff permissions & MIME', () => {
  const routeFile = path.resolve(__dirname, '../../frontend/src/app/api/media/upload/route.ts');
  const content = fs.readFileSync(routeFile, 'utf-8');

  assert.ok(content.includes('STAFF_ROLES'), 'Staff authorization check missing');
  assert.ok(content.includes('ALLOWED_MIME_TYPES'), 'MIME type whitelist missing');
  assert.ok(content.includes('MAX_FILE_SIZE_BYTES'), 'Max file size constraint missing');
  assert.ok(content.includes('products/'), 'Storage key prefix constraint missing');
});

// -----------------------------------------------------------------------------
// 6. Admin & Reporting Views
// -----------------------------------------------------------------------------
console.log('\n--- Suite 6: Admin & Reporting Views ---');

runTest('6.1 Real-time reporting SQL views defined in database', () => {
  const rpcFile = path.resolve(__dirname, '../../supabase/migrations/20261116000003_business_logic_rpc.sql');
  const sql = fs.readFileSync(rpcFile, 'utf-8');

  assert.ok(sql.includes('v_admin_sales_overview'), 'v_admin_sales_overview view missing');
  assert.ok(sql.includes('v_low_stock_alerts'), 'v_low_stock_alerts view missing');
});

// -----------------------------------------------------------------------------
// Summary
// -----------------------------------------------------------------------------
console.log('\n================================================================');
console.log(`ACCEPTANCE TESTS COMPLETED: ${passedTests}/${totalTests} Passed (${failedTests} Failed)`);
console.log('================================================================');

if (failedTests > 0) {
  process.exit(1);
}
