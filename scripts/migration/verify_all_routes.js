/**
 * Comprehensive Route Verification Script
 * Validates that all storefront and admin routes load successfully (HTTP 200)
 * and show graceful fallback/error states on non-existent resources.
 */

const http = require('http');

const ROUTES = [
  // Storefront Core
  { path: '/', label: 'Homepage' },
  { path: '/collections/all', label: 'All Collections' },
  { path: '/collections/men', label: "Men's Collection" },
  { path: '/collections/women', label: "Women's Collection" },
  { path: '/collections/men-t-shirts', label: "Men's T-Shirts (reported issue)" },
  { path: '/collections/men-hoodies', label: "Men's Hoodies" },
  { path: '/collections/men-jackets', label: "Men's Jackets" },
  { path: '/collections/footwear', label: 'Footwear (Coming Soon)' },
  { path: '/collections/accessories', label: 'Accessories (Coming Soon)' },
  { path: '/collections/non-existent-cat', label: 'Unknown Category (Fallback Graceful)' },
  { path: '/cart', label: 'Shopping Cart' },
  { path: '/checkout', label: 'Checkout Form' },
  { path: '/wishlist', label: 'Wishlist' },
  { path: '/account', label: 'Customer Account' },

  // Static CMS Pages
  { path: '/about', label: 'About Brand' },
  { path: '/contact', label: 'Contact Us' },
  { path: '/faqs', label: 'FAQs' },
  { path: '/shipping-delivery', label: 'Shipping & Delivery Policy' },
  { path: '/returns-exchanges', label: 'Returns & Exchanges' },
  { path: '/privacy-policy', label: 'Privacy Policy' },
  { path: '/terms', label: 'Terms of Service' },

  // Admin & Staff Portals
  { path: '/admin', label: 'Admin Dashboard Overview' },
  { path: '/admin/products', label: 'Admin Product Catalog' },
  { path: '/admin/products/new', label: 'Admin New Product Creator' },
  { path: '/admin/products/1/edit', label: 'Admin Product Editor' },
  { path: '/admin/categories', label: 'Admin Category Manager' },
  { path: '/admin/orders', label: 'Admin Order Processing' },
  { path: '/admin/pos', label: 'Admin Point-of-Sale Terminal' },
  { path: '/admin/payments', label: 'Admin Payment Records' },
  { path: '/admin/customers', label: 'Admin Customer Directory' },
  { path: '/admin/returns', label: 'Admin Returns Resolution' },
  { path: '/admin/audit-logs', label: 'Admin Audit Log Vault' },
  { path: '/staff', label: 'Staff Orders & Stock Portal' },
];

async function checkRoute(route) {
  return new Promise((resolve) => {
    const req = http.get(
      `http://localhost:3000${route.path}`,
      { headers: { 'User-Agent': 'UwearNova-Route-Verifier' } },
      (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => {
          const hasErrorMarker = body.includes('Internal Server Error') || body.includes('Application error');
          resolve({
            path: route.path,
            label: route.label,
            status: res.statusCode,
            ok: res.statusCode === 200 && !hasErrorMarker,
          });
        });
      }
    );

    req.on('error', (err) => {
      resolve({
        path: route.path,
        label: route.label,
        status: 0,
        ok: false,
        error: err.message,
      });
    });
  });
}

async function run() {
  console.log('================================================================');
  console.log('       UWEARNOVA: COMPREHENSIVE ROUTE VERIFICATION SUITE        ');
  console.log('================================================================\n');

  let passed = 0;
  let failed = 0;

  for (const route of ROUTES) {
    const res = await checkRoute(route);
    if (res.ok) {
      console.log(`[PASS] HTTP ${res.status} | ${res.path.padEnd(35)} -> ${res.label}`);
      passed++;
    } else {
      console.error(`[FAIL] HTTP ${res.status} | ${res.path.padEnd(35)} -> ${res.label} (${res.error || 'Server error'})`);
      failed++;
    }
  }

  console.log('\n================================================================');
  console.log(`ROUTE VERIFICATION SUMMARY: ${passed}/${ROUTES.length} Routes Passed (${failed} Failed)`);
  console.log('================================================================');

  if (failed > 0) process.exit(1);
}

run();
