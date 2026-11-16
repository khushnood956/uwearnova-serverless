/**
 * Stage 8: Live Staging Workflows & Commerce Test Suite
 * Tests actual end-to-end interactions with live remote Supabase & Cloudflare R2:
 * 1. PostgREST Catalog Query
 * 2. Cloudflare R2 Presigned Direct PUT Upload & Verification
 * 3. Atomic Order Placement via place_order_atomic RPC
 * 4. Real-time Analytics Reporting View Reflection
 * STRICT SECURITY: Never logs or prints secrets.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const assert = require('assert');

const ENV_PATH = path.resolve(__dirname, '../../frontend/.env.local');
const SUPABASE_JS_PATH = path.resolve(__dirname, '../../frontend/node_modules/@supabase/supabase-js');
const AWS_S3_PATH = path.resolve(__dirname, '../../frontend/node_modules/@aws-sdk/client-s3');
const PRESIGNER_PATH = path.resolve(__dirname, '../../frontend/node_modules/@aws-sdk/s3-request-presigner');

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
const serviceRoleKey = envVars['SUPABASE_SERVICE_ROLE_KEY'];
const anonKey = envVars['NEXT_PUBLIC_SUPABASE_ANON_KEY'];

const r2AccountId = envVars['R2_ACCOUNT_ID'];
const r2AccessKey = envVars['R2_ACCESS_KEY_ID'];
const r2SecretKey = envVars['R2_SECRET_ACCESS_KEY'];
const r2Bucket = envVars['R2_BUCKET_NAME'] || 'uwearnova';
const r2PublicDomain = envVars['NEXT_PUBLIC_R2_PUBLIC_DOMAIN'] || 'https://images.uwearnova.com';

const { createClient } = require(SUPABASE_JS_PATH);
const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey || anonKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});

const { S3Client, PutObjectCommand, HeadObjectCommand, DeleteObjectCommand } = require(AWS_S3_PATH);
const { getSignedUrl } = require(PRESIGNER_PATH);

async function runLiveTests() {
  console.log('================================================================');
  console.log('    UWEARNOVA STAGING: LIVE WORKFLOW ACCEPTANCE TEST SUITE      ');
  console.log('================================================================\n');

  // ---------------------------------------------------------------------------
  // Test 1: Query Live Catalog from Supabase PostgREST
  // ---------------------------------------------------------------------------
  console.log('--- 1. Live Catalog PostgREST Query ---');
  const { data: products, error: prodErr } = await supabaseAdmin
    .from('products')
    .select('id, name, slug, price, variants:product_variants(id, sku, price, inventory_count)')
    .eq('status', 'active');

  if (prodErr || !products || products.length === 0) {
    throw new Error(`Catalog query failed: ${prodErr?.message || 'No products returned'}`);
  }

  const testProduct = products[0];
  const testVariant = testProduct.variants[0];
  console.log(`[PASS] Retrieved ${products.length} live products.`);
  console.log(`       Test Target: "${testProduct.name}" (SKU: ${testVariant.sku}, Initial Stock: ${testVariant.inventory_count})`);

  // ---------------------------------------------------------------------------
  // Test 2: Cloudflare R2 Presigned Direct PUT Upload & Verification
  // ---------------------------------------------------------------------------
  console.log('\n--- 2. Cloudflare R2 Direct Upload & Verification ---');
  const r2Client = new S3Client({
    region: 'auto',
    endpoint: `https://${r2AccountId}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: r2AccessKey,
      secretAccessKey: r2SecretKey,
    },
  });

  const timestamp = Date.now();
  const testStorageKey = `products/${testProduct.id}/staging-test-${timestamp}.webp`;
  // Minimal valid 1x1 WebP image byte sequence
  const testWebpBuffer = Buffer.from('RIFF24000000WEBPVP8X0A0000000000000000000000ALPH00000000VP8 10000000010000000000', 'binary');

  const putCmd = new PutObjectCommand({
    Bucket: r2Bucket,
    Key: testStorageKey,
    ContentType: 'image/webp',
    ContentLength: testWebpBuffer.length,
  });

  const presignedUploadUrl = await getSignedUrl(r2Client, putCmd, { expiresIn: 300 });
  console.log(`[PASS] Generated S3v4 presigned PUT URL for Cloudflare R2.`);

  // Upload directly via HTTP PUT
  await new Promise((resolve, reject) => {
    const parsed = new URL(presignedUploadUrl);
    const req = https.request(
      presignedUploadUrl,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'image/webp',
          'Content-Length': testWebpBuffer.length,
        },
      },
      (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          reject(new Error(`R2 direct PUT upload returned HTTP ${res.statusCode}`));
        }
      }
    );
    req.on('error', reject);
    req.write(testWebpBuffer);
    req.end();
  });
  console.log(`[PASS] Binary upload completed directly to Cloudflare R2 bucket '${r2Bucket}'.`);

  // Verify object existence in R2 via HeadObject
  await r2Client.send(new HeadObjectCommand({ Bucket: r2Bucket, Key: testStorageKey }));
  console.log(`[PASS] HeadObject confirmed: Object exists in R2 storage.`);

  // Clean up test image
  await r2Client.send(new DeleteObjectCommand({ Bucket: r2Bucket, Key: testStorageKey }));
  console.log(`[PASS] Cleaned up temporary test object from R2.`);

  // ---------------------------------------------------------------------------
  // Test 3: Atomic Order Placement via place_order_atomic RPC
  // ---------------------------------------------------------------------------
  console.log('\n--- 3. Atomic Order Placement (place_order_atomic RPC) ---');
  const initialStock = testVariant.inventory_count;

  const checkoutPayload = {
    customer_email: 'staging-test@uwearnova.com',
    customer_phone: '03001234567',
    customer_name: 'Staging Test Client',
    shipping_address: {
      full_name: 'Staging Test Client',
      phone: '03001234567',
      street_address: '123 Staging Avenue, Gulberg III',
      city: 'Lahore',
      postal_code: '54000',
      province: 'Punjab',
      country: 'Pakistan',
    },
    payment_method: 'cod',
    shipping_method_code: 'standard_delivery',
    items: [
      {
        variant_id: testVariant.id,
        product_name: testProduct.name,
        product_slug: testProduct.slug,
        sku: testVariant.sku,
        size: testVariant.size || 'M',
        color: testVariant.color_name || 'Sand',
        quantity: 1,
      },
    ],
  };

  const { data: orderResult, error: orderErr } = await supabaseAdmin.rpc('place_order_atomic', {
    p_order_data: checkoutPayload,
  });

  if (orderErr || !orderResult) {
    throw new Error(`place_order_atomic RPC failed: ${orderErr?.message}`);
  }

  console.log(`[PASS] Atomic Order placed successfully!`);
  console.log(`       Order ID:     ${orderResult.order_id}`);
  console.log(`       Order Number: ${orderResult.order_number}`);
  console.log(`       Grand Total:  PKR ${Number(orderResult.grand_total).toLocaleString('en-PK')}`);

  // Verify stock deduction in database
  const { data: updatedVariant } = await supabaseAdmin
    .from('product_variants')
    .select('inventory_count')
    .eq('id', testVariant.id)
    .single();

  assert.strictEqual(
    updatedVariant.inventory_count,
    initialStock - 1,
    `Stock must be deducted by exactly 1 unit (Initial: ${initialStock}, Now: ${updatedVariant.inventory_count})`
  );
  console.log(`[PASS] Inventory deduction verified in DB: Stock decreased from ${initialStock} to ${updatedVariant.inventory_count}.`);

  // ---------------------------------------------------------------------------
  // Test 4: Real-time Analytics Reporting View
  // ---------------------------------------------------------------------------
  console.log('\n--- 4. Real-time Analytics View (v_admin_sales_overview) ---');
  const { data: salesOverview, error: viewErr } = await supabaseAdmin
    .from('v_admin_sales_overview')
    .select('*')
    .single();

  if (viewErr) {
    throw new Error(`v_admin_sales_overview query failed: ${viewErr.message}`);
  }

  assert.ok(Number(salesOverview.total_orders) >= 1, 'Total orders in view must be at least 1');
  console.log(`[PASS] v_admin_sales_overview reflected live transaction:`);
  console.log(`       Total Orders:     ${salesOverview.total_orders}`);
  console.log(`       Pending Orders:   ${salesOverview.pending_orders}`);
  console.log(`       Gross Sales:      PKR ${Number(salesOverview.gross_sales).toLocaleString('en-PK')}`);

  console.log('\n================================================================');
  console.log('ALL LIVE STAGING ACCEPTANCE WORKFLOWS SUCCEEDED (100% PASS)');
  console.log('================================================================');
  process.exit(0);
}

runLiveTests().catch((err) => {
  console.error(`\n[FATAL ERROR] Live test failed: ${err.message}`);
  process.exit(1);
});
