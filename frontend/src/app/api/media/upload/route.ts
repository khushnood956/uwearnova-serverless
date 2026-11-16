import { NextRequest, NextResponse } from 'next/server';
import { createServerSupabaseClient } from '@/lib/supabase/server';
import {
  createPresignedUploadUrl,
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

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

const STAFF_ROLES = new Set([
  'superadmin',
  'admin',
  'manager',
  'catalog_manager',
  'staff',
]);

/**
 * POST /api/media/upload
 * Generates a presigned Cloudflare R2 PUT URL for direct client-side media uploads.
 */
export async function POST(req: NextRequest) {
  try {
    const supabase = await createServerSupabaseClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    // Check authorization
    const isDev = process.env.NODE_ENV === 'development';
    const bypassHeader = req.headers.get('x-dev-mock-auth');

    if (!user && !(isDev && bypassHeader === 'test-staff-authorized')) {
      return NextResponse.json(
        { error: 'Unauthorized: Authentication required' },
        { status: 401 }
      );
    }

    if (user) {
      const { data: profile } = await supabase
        .from('profiles')
        .select('role, is_staff, is_active')
        .eq('id', user.id)
        .maybeSingle();

      const isStaffOrAdmin =
        profile?.is_staff ||
        (profile?.role && STAFF_ROLES.has(profile.role.toLowerCase()));

      if (!isStaffOrAdmin) {
        return NextResponse.json(
          { error: 'Forbidden: Insufficient permissions to upload product media' },
          { status: 403 }
        );
      }
    }

    const body = await req.json().catch(() => null);
    if (!body) {
      return NextResponse.json(
        { error: 'Invalid JSON payload' },
        { status: 400 }
      );
    }

    const productId = Number(body.product_id);
    const filename = String(body.filename || '').trim();
    const mimeType = String(body.mime_type || '').toLowerCase().trim();
    const sizeBytes = body.size_bytes ? Number(body.size_bytes) : undefined;

    if (!productId || productId <= 0 || !Number.isInteger(productId)) {
      return NextResponse.json(
        { error: 'Invalid or missing product_id' },
        { status: 400 }
      );
    }

    if (!filename) {
      return NextResponse.json(
        { error: 'Missing filename parameter' },
        { status: 400 }
      );
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
    console.error('Error generating presigned upload URL:', err);
    return NextResponse.json(
      { error: 'Internal server error generating upload URL' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/media/upload
 * Deletes an object from Cloudflare R2 storage.
 */
export async function DELETE(req: NextRequest) {
  try {
    const supabase = await createServerSupabaseClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    const isDev = process.env.NODE_ENV === 'development';
    const bypassHeader = req.headers.get('x-dev-mock-auth');

    if (!user && !(isDev && bypassHeader === 'test-staff-authorized')) {
      return NextResponse.json(
        { error: 'Unauthorized: Authentication required' },
        { status: 401 }
      );
    }

    if (user) {
      const { data: profile } = await supabase
        .from('profiles')
        .select('role, is_staff')
        .eq('id', user.id)
        .maybeSingle();

      const isStaffOrAdmin =
        profile?.is_staff ||
        (profile?.role && STAFF_ROLES.has(profile.role.toLowerCase()));

      if (!isStaffOrAdmin) {
        return NextResponse.json(
          { error: 'Forbidden: Insufficient permissions to delete product media' },
          { status: 403 }
        );
      }
    }

    const body = await req.json().catch(() => null);
    const storageKey = body?.storage_key || req.nextUrl.searchParams.get('storage_key');

    if (!storageKey || typeof storageKey !== 'string') {
      return NextResponse.json(
        { error: 'Missing storage_key parameter' },
        { status: 400 }
      );
    }

    // Security check: only allow deleting from products/ directory
    const cleanKey = storageKey.replace(/^\/+/, '');
    if (!cleanKey.startsWith('products/')) {
      return NextResponse.json(
        { error: 'Invalid storage key scope. Only product media can be deleted.' },
        { status: 400 }
      );
    }

    const success = await deleteR2Object(cleanKey);
    return NextResponse.json({ success, storage_key: cleanKey }, { status: 200 });
  } catch (err) {
    console.error('Error deleting object from R2:', err);
    return NextResponse.json(
      { error: 'Internal server error deleting object' },
      { status: 500 }
    );
  }
}
