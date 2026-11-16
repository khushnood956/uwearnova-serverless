/**
 * Stage 7.1: Staging Credentials & Connectivity Verification Script
 * Validates format, syntax, and remote connectivity of Supabase & Cloudflare R2
 * STRICT SECURITY PROTOCOL: Never prints, logs, or exports secret values.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ENV_PATH = path.resolve(__dirname, '../../frontend/.env.local');

console.log('================================================================');
console.log('    UNINOVA STAGING CREDENTIALS & CONNECTIVITY VERIFICATION     ');
console.log('================================================================\n');

if (!fs.existsSync(ENV_PATH)) {
  console.error('[ERROR] frontend/.env.local not found. Please create the file.');
  process.exit(1);
}

// Parse env file without logging values
const envContent = fs.readFileSync(ENV_PATH, 'utf-8');
const envVars = {};

envContent.split(/\r?\n/).forEach((line) => {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#')) return;
  const match = trimmed.match(/^([^=]+)=(.*)$/);
  if (match) {
    const key = match[1].trim();
    let val = match[2].trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    envVars[key] = val;
  }
});

let errors = 0;
let warnings = 0;

// Helper: mask sensitive values (shows only first 4 chars, NEVER full key)
function isConfigured(val, placeholderText) {
  return val && val !== placeholderText && !val.includes('your-') && !val.includes('placeholder');
}

// 1. Verify Supabase URL
console.log('--- 1. Supabase Project Configuration ---');
const supabaseUrl = envVars['NEXT_PUBLIC_SUPABASE_URL'];
if (isConfigured(supabaseUrl, 'https://your-project-ref.supabase.co')) {
  try {
    const parsed = new URL(supabaseUrl);
    if (parsed.protocol === 'https:' && parsed.hostname.endsWith('.supabase.co')) {
      console.log(`[PASS] Supabase URL: Valid format (https://***.supabase.co)`);
    } else {
      console.log(`[PASS] Supabase URL: Custom or self-hosted endpoint detected (${parsed.hostname})`);
    }
  } catch {
    console.error(`[FAIL] Supabase URL: Invalid URL syntax.`);
    errors++;
  }
} else {
  console.log(`[WAITING] Supabase URL is not configured yet (contains placeholder).`);
  warnings++;
}

// 2. Verify Supabase Anon Key
const anonKey = envVars['NEXT_PUBLIC_SUPABASE_ANON_KEY'];
if (isConfigured(anonKey, 'your-anon-public-key-here')) {
  const parts = anonKey.split('.');
  if (parts.length === 3 && anonKey.startsWith('ey')) {
    console.log(`[PASS] Supabase Anon Key: Valid JWT structure verified.`);
  } else {
    console.warn(`[WARN] Supabase Anon Key does not appear to follow standard JWT structure.`);
    warnings++;
  }
} else {
  console.log(`[WAITING] Supabase Anon Key is not configured yet.`);
  warnings++;
}

// 3. Verify Supabase Service Role Key
const serviceRoleKey = envVars['SUPABASE_SERVICE_ROLE_KEY'];
if (isConfigured(serviceRoleKey, 'your-service-role-secret-key-here')) {
  const parts = serviceRoleKey.split('.');
  if (parts.length === 3 && serviceRoleKey.startsWith('ey')) {
    console.log(`[PASS] Supabase Service Role Key: Valid JWT structure verified.`);
  } else {
    console.warn(`[WARN] Supabase Service Role Key does not appear to follow standard JWT structure.`);
    warnings++;
  }
} else {
  console.log(`[WAITING] Supabase Service Role Key is not configured yet.`);
  warnings++;
}

// 4. Verify Cloudflare R2 Credentials (Optional)
console.log('\n--- 2. Cloudflare R2 Configuration ---');
const r2AccountId = envVars['R2_ACCOUNT_ID'];
const r2AccessKey = envVars['R2_ACCESS_KEY_ID'];
const r2SecretKey = envVars['R2_SECRET_ACCESS_KEY'];
const r2Bucket = envVars['R2_BUCKET_NAME'];

if (isConfigured(r2AccountId, 'your-cloudflare-account-id-here')) {
  console.log(`[PASS] R2 Account ID: Configured (${r2AccountId.length} chars).`);
} else {
  console.log(`[INFO] R2 Account ID: Unconfigured (Optional fallback active).`);
}

if (isConfigured(r2AccessKey, 'your-r2-access-key-id-here')) {
  console.log(`[PASS] R2 Access Key ID: Configured.`);
} else {
  console.log(`[INFO] R2 Access Key ID: Unconfigured (Optional fallback active).`);
}

if (isConfigured(r2SecretKey, 'your-r2-secret-access-key-here')) {
  console.log(`[PASS] R2 Secret Access Key: Configured.`);
} else {
  console.log(`[INFO] R2 Secret Access Key: Unconfigured (Optional fallback active).`);
}

if (isConfigured(r2Bucket, 'uninova-media')) {
  console.log(`[PASS] R2 Bucket Name: Configured (${r2Bucket}).`);
} else {
  console.log(`[INFO] R2 Bucket Name: Default 'uninova-media'.`);
}

// 5. Test Remote Supabase REST Connectivity (If configured)
console.log('\n--- 3. Remote Connectivity Test ---');
if (
  isConfigured(supabaseUrl, 'https://your-project-ref.supabase.co') &&
  isConfigured(anonKey, 'your-anon-public-key-here')
) {
  console.log('Testing remote connection to Supabase REST API...');
  const pingUrl = `${supabaseUrl.replace(/\/+$/, '')}/rest/v1/`;

  try {
    const req = https.request(
      pingUrl,
      {
        method: 'GET',
        headers: {
          apikey: anonKey,
          Authorization: `Bearer ${anonKey}`,
        },
        timeout: 8000,
      },
      (res) => {
        if (res.statusCode === 200) {
          console.log(`[SUCCESS] Connected to Supabase REST Gateway (HTTP 200 OK).`);
        } else if (res.statusCode === 401 || res.statusCode === 403) {
          console.error(`[FAIL] Connected but received HTTP ${res.statusCode}. Check that your Anon Key matches the project.`);
          errors++;
        } else {
          console.log(`[INFO] Gateway responded with HTTP ${res.statusCode}.`);
        }
        summarize();
      }
    );

    req.on('error', (err) => {
      console.error(`[FAIL] Connection failed: ${err.message}`);
      errors++;
      summarize();
    });

    req.on('timeout', () => {
      req.destroy();
      console.error(`[FAIL] Connection timed out after 8 seconds.`);
      errors++;
      summarize();
    });

    req.end();
  } catch (err) {
    console.error(`[FAIL] Ping error: ${err.message}`);
    errors++;
    summarize();
  }
} else {
  console.log('[SKIPPED] Remote connectivity ping skipped (waiting for credentials).');
  summarize();
}

function summarize() {
  console.log('\n================================================================');
  if (errors > 0) {
    console.log(`VERIFICATION COMPLETED: ${errors} error(s) found. Check details above.`);
  } else if (warnings > 0) {
    console.log(`VERIFICATION COMPLETED: Ready for credentials. Paste them in frontend/.env.local`);
  } else {
    console.log(`VERIFICATION COMPLETED: All configured credentials verified successfully!`);
  }
  console.log('================================================================');
}
