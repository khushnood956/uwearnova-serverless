import { NextRequest, NextResponse } from 'next/server';
import { createServerSupabaseClient } from '@/lib/supabase/server';
import { createAdminClient } from '@/lib/supabase/admin';
import {
  createPresignedUploadUrl,
  uploadR2Buffer,
  deleteR2Object,
  PresignedUploadOptions,
} from '@/lib/storage/r2';

const ALLOWED_MIME_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/avif',
  'image/gif',
]);

const MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024; // 15 MB

/**
 * Helper to authenticate and verify staff or admin clearance
 */
async function verifyStaffOrAdmin(req: NextRequest) {
  // 1. Try cookie session from createServerSupabaseClient
  const supabase = await createServerSupabaseClient();
  let {
    data: { user },
  } = await supabase.auth.getUser();

  // 2. Fallback to Bearer token from Authorization header if cookie session is empty
  if (!user) {
    const authHeader = req.headers.get('authorization');
    const token = authHeader?.replace(/^Bearer\s+/i, '');
    if (token) {
      try {
        const supabaseAdmin = createAdminClient();
        const { data: tokenData } = await supabaseAdmin.auth.getUser(token);
        user = tokenData?.user || null;
      } catch {
        // ignore token lookup error
      }
    }
  }

  const isDev = process.env.NODE_ENV === 'development';
  const bypassHeader = req.headers.get('x-dev-mock-auth');
  if (!user && isDev && bypassHeader === 'test-staff-authorized') {
    return { authorized: true, user: null };
  }

  if (!user) {
    return { authorized: false, error: 'Unauthorized: Authentication required', status: 401 };
  }

  // 3. Check user metadata or known staff domain
  const metaType = user.user_metadata?.user_type;
  const email = user.email?.toLowerCase() || '';

  if (metaType === 'admin' || metaType === 'staff' || email.endsWith('@uwearnova.com')) {
    return { authorized: true, user };
  }

  // 4. Verify in public.users table via admin client
  try {
    const supabaseAdmin = createAdminClient();
    const { data: domainUser } = await supabaseAdmin
      .from('users')
      .select('id, user_type, status')
      .eq('auth_user_id', user.id)
      .maybeSingle();

    if (domainUser && (domainUser.user_type === 'admin' || domainUser.user_type === 'staff')) {
      return { authorized: true, user };
    }
  } catch (err) {
    console.warn('Database user clearance lookup error:', err);
  }

  return {
    authorized: false,
    error: 'Forbidden: Insufficient permissions to upload product media',
    status: 403,
  };
}

/**
 * POST /api/media/upload
 * Supports two modes:
 * A) multipart/form-data: Direct server-side upload to Cloudflare R2 + DB registration (bypasses browser CORS)
 * B) application/json: Presigned Cloudflare R2 PUT URL for direct client uploads
 */
export async function POST(req: NextRequest) {
  try {
    const authCheck = await verifyStaffOrAdmin(req);
    if (!authCheck.authorized) {
      return NextResponse.json(
        { error: authCheck.error },
        { status: authCheck.status }
      );
    }

    const contentType = req.headers.get('content-type') || '';

    // =========================================================================
    // MODE A: Direct Multipart Upload (Robust against browser CORS)
    // =========================================================================
    if (contentType.includes('multipart/form-data')) {
      const formData = await req.formData();
      const file = formData.get('file') as File | null;
      const productId = Number(formData.get('product_id'));
      const altText = (formData.get('alt_text') as string) || '';
      const isPrimary = formData.get('is_primary') === 'true';
      const sortOrder = Number(formData.get('sort_order') || 0);

      if (!file || !(file instanceof File)) {
        return NextResponse.json({ error: 'No valid file provided' }, { status: 400 });
      }

      if (!productId || productId <= 0 || !Number.isInteger(productId)) {
        return NextResponse.json({ error: 'Invalid or missing product_id' }, { status: 400 });
      }

      const mimeType = (file.type || 'image/jpeg').toLowerCase().trim();
      if (!ALLOWED_MIME_TYPES.has(mimeType)) {
        return NextResponse.json(
          {
            error: `Unsupported MIME type: '${mimeType}'. Allowed: ${Array.from(ALLOWED_MIME_TYPES).join(', ')}`,
          },
          { status: 400 }
        );
      }

      if (file.size <= 0 || file.size > MAX_FILE_SIZE_BYTES) {
        return NextResponse.json(
          {
            error: `File size exceeds maximum allowed limit of ${MAX_FILE_SIZE_BYTES / (1024 * 1024)} MB`,
          },
          { status: 400 }
        );
      }

      // Direct upload buffer to Cloudflare R2
      const arrayBuffer = await file.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);
      const { storageKey, publicUrl } = await uploadR2Buffer(buffer, {
        productId,
        filename: file.name,
        mimeType,
      });

      // Register image in Supabase product_images using admin client
      const supabaseAdmin = createAdminClient();
      if (isPrimary) {
        await supabaseAdmin
          .from('product_images')
          .update({ is_primary: false })
          .eq('product_id', productId);
      }

      const { data: imgRecord, error: dbErr } = await supabaseAdmin
        .from('product_images')
        .insert({
          product_id: productId,
          image_url: publicUrl,
          alt_text: altText || file.name.replace(/\.[^/.]+$/, ''),
          is_primary: isPrimary,
          sort_order: sortOrder,
        })
        .select('*')
        .single();

      if (dbErr) {
        console.error('Failed to register image in database:', dbErr);
        return NextResponse.json({ error: dbErr.message }, { status: 500 });
      }

      return NextResponse.json(
        {
          success: true,
          image: imgRecord,
          public_url: publicUrl,
          storage_key: storageKey,
        },
        { status: 201 }
      );
    }

    // =========================================================================
    // MODE B: Presigned URL Intent (JSON payload)
    // =========================================================================
    const body = await req.json().catch(() => null);
    if (!body) {
      return NextResponse.json({ error: 'Invalid JSON payload' }, { status: 400 });
    }

    const productId = Number(body.product_id);
    const filename = String(body.filename || '').trim();
    const mimeType = String(body.mime_type || '').toLowerCase().trim();
    const sizeBytes = body.size_bytes ? Number(body.size_bytes) : undefined;

    if (!productId || productId <= 0 || !Number.isInteger(productId)) {
      return NextResponse.json({ error: 'Invalid or missing product_id' }, { status: 400 });
    }

    if (!filename) {
      return NextResponse.json({ error: 'Missing filename parameter' }, { status: 400 });
    }

    if (!ALLOWED_MIME_TYPES.has(mimeType)) {
      return NextResponse.json(
        {
          error: `Unsupported MIME type: '${mimeType}'. Allowed: ${Array.from(ALLOWED_MIME_TYPES).join(', ')}`,
        },
        { status: 400 }
      );
    }

    if (sizeBytes !== undefined) {
      if (sizeBytes <= 0 || sizeBytes > MAX_FILE_SIZE_BYTES) {
        return NextResponse.json(
          {
            error: `File size exceeds maximum allowed limit of ${MAX_FILE_SIZE_BYTES / (1024 * 1024)} MB`,
          },
          { status: 400 }
        );
      }
    }

    const uploadOptions: PresignedUploadOptions = {
      productId,
      filename,
      mimeType,
      sizeBytes,
      expiresInSeconds: 900, // 15 minutes
    };

    const presigned = await createPresignedUploadUrl(uploadOptions);

    return NextResponse.json(presigned, { status: 200 });
  } catch (err) {
    console.error('Error handling media upload:', err);
    return NextResponse.json(
      { error: 'Internal server error processing media upload' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/media/upload
 * Deletes an object from Cloudflare R2 storage and removes image record from database.
 */
export async function DELETE(req: NextRequest) {
  try {
    const authCheck = await verifyStaffOrAdmin(req);
    if (!authCheck.authorized) {
      return NextResponse.json(
        { error: authCheck.error },
        { status: authCheck.status }
      );
    }

    const body = await req.json().catch(() => null);
    const storageKey = body?.storage_key || req.nextUrl.searchParams.get('storage_key');
    const imageId = body?.image_id || req.nextUrl.searchParams.get('image_id');

    if (!storageKey && !imageId) {
      return NextResponse.json(
        { error: 'Missing storage_key or image_id parameter' },
        { status: 400 }
      );
    }

    let success = true;
    if (storageKey && typeof storageKey === 'string') {
      const cleanKey = storageKey.replace(/^\/+/, '');
      if (cleanKey.startsWith('products/')) {
        success = await deleteR2Object(cleanKey);
      }
    }

    if (imageId) {
      const supabaseAdmin = createAdminClient();
      await supabaseAdmin.from('product_images').delete().eq('id', Number(imageId));
    }

    return NextResponse.json({ success, storage_key: storageKey }, { status: 200 });
  } catch (err) {
    console.error('Error deleting object from R2:', err);
    return NextResponse.json(
      { error: 'Internal server error deleting object' },
      { status: 500 }
    );
  }
}
