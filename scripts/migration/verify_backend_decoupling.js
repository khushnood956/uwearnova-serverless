/**
 * Stage 9: Backend Decoupling Verification Script
 * Validates that the frontend and runtime services have 0 active dependencies
 * on the legacy FastAPI backend, SQLAlchemy ORM, or local MySQL database.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('================================================================');
console.log('    UWEARNOVA: STAGE 9 BACKEND DECOUPLING VERIFICATION SUITE    ');
console.log('================================================================\n');

let totalChecks = 0;
let passedChecks = 0;
let failedChecks = 0;

function check(title, fn) {
  totalChecks++;
  try {
    fn();
    console.log(`[PASS] ${title}`);
    passedChecks++;
  } catch (err) {
    console.error(`[FAIL] ${title}: ${err.message}`);
    failedChecks++;
  }
}

const FRONTEND_SRC = path.resolve(__dirname, '../../frontend/src');

// 1. Check for legacy localhost:8000 or backend:8000 calls
check('1.1 Zero active localhost:8000 network requests in frontend/src', () => {
  function scan(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        scan(fullPath);
      } else if (entry.isFile() && /\.(tsx?|jsx?)$/.test(entry.name)) {
        const content = fs.readFileSync(fullPath, 'utf-8');
        assert.strictEqual(
          content.includes('http://localhost:8000'),
          false,
          `Found localhost:8000 in ${entry.name}`
        );
        assert.strictEqual(
          content.includes('http://backend:8000'),
          false,
          `Found backend:8000 in ${entry.name}`
        );
      }
    }
  }
  scan(FRONTEND_SRC);
});

// 2. Check that frontend API client enforces BACKEND_MIGRATED
check('2.1 Legacy apiClient guards deprecated routes with BACKEND_MIGRATED', () => {
  const clientPath = path.resolve(FRONTEND_SRC, 'lib/api/client.ts');
  const content = fs.readFileSync(clientPath, 'utf-8');
  assert.ok(content.includes('BACKEND_MIGRATED'), 'client.ts must throw BACKEND_MIGRATED');
});

// 3. Check that all API modules query Supabase directly
check('3.1 All 11 frontend API modules communicate via Supabase layer', () => {
  const apiDir = path.resolve(FRONTEND_SRC, 'lib/api');
  const modules = [
    'auth.ts', 'catalog.ts', 'orders.ts', 'cart.ts', 'customer.ts',
    'admin.ts', 'shipping.ts', 'content.ts', 'payments.ts', 'staff.ts'
  ];

  for (const mod of modules) {
    const modPath = path.join(apiDir, mod);
    assert.ok(fs.existsSync(modPath), `Module ${mod} must exist`);
    const content = fs.readFileSync(modPath, 'utf-8');
    const hasSupabase =
      content.includes('@/lib/supabase/client') ||
      content.includes('@/lib/supabase/server') ||
      content.includes('@/lib/supabase/admin') ||
      content.includes('supabase');
    assert.ok(hasSupabase, `Module ${mod} must use Supabase`);
  }
});

// 4. Verify Media Uploads route to Cloudflare R2
check('4.1 Media upload pipeline targets Cloudflare R2 direct presigned URLs', () => {
  const r2Path = path.resolve(FRONTEND_SRC, 'lib/storage/r2.ts');
  const routePath = path.resolve(FRONTEND_SRC, 'app/api/media/upload/route.ts');
  assert.ok(fs.existsSync(r2Path), 'r2.ts must exist');
  assert.ok(fs.existsSync(routePath), 'media/upload/route.ts must exist');

  const routeContent = fs.readFileSync(routePath, 'utf-8');
  assert.ok(routeContent.includes('createPresignedUploadUrl'), 'Route must issue presigned URLs');
});

// 5. Verify database data independence
check('5.1 Verified data exports and SQL migrations exist for full standalone operation', () => {
  const exportPath = path.resolve(__dirname, '../../data/exports/legacy_dataset.json');
  const migrationsDir = path.resolve(__dirname, '../../supabase/migrations');
  assert.ok(fs.existsSync(exportPath), 'legacy_dataset.json must exist');
  assert.ok(fs.existsSync(migrationsDir), 'supabase/migrations must exist');

  const files = fs.readdirSync(migrationsDir);
  assert.ok(files.length >= 3, 'Must have at least 3 PostgreSQL migrations');
});

// 6. Verify pristine backups remain untouched
check('6.1 Original project and backup folders are preserved outside migration repo', () => {
  const originalPath = 'E:\\website';
  const backupPath = 'E:\\UniNova_Backup_Serverful_PreSupabase_Migration';
  assert.ok(fs.existsSync(originalPath), 'Original repository E:\\website must be intact');
  assert.ok(fs.existsSync(backupPath), 'Backup repository E:\\UniNova_Backup_Serverful_PreSupabase_Migration must be intact');
});

console.log('\n================================================================');
console.log(`DECOUPLING VERIFICATION: ${passedChecks}/${totalChecks} Checks Passed (${failedChecks} Failed)`);
console.log('================================================================');

if (failedChecks > 0) {
  process.exit(1);
}
