import { S3Client, PutObjectCommand, DeleteObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const R2_ACCOUNT_ID = process.env.R2_ACCOUNT_ID || '';
const R2_ACCESS_KEY_ID = process.env.R2_ACCESS_KEY_ID || '';
const R2_SECRET_ACCESS_KEY = process.env.R2_SECRET_ACCESS_KEY || '';
const R2_BUCKET_NAME = process.env.R2_BUCKET_NAME || 'uwearnova';
const R2_PUBLIC_DOMAIN = (
  process.env.NEXT_PUBLIC_R2_PUBLIC_DOMAIN ||
  process.env.R2_PUBLIC_DOMAIN ||
  'https://images.uwearnova.com'
).replace(/\/+$/, '');

/**
 * Singleton Cloudflare R2 S3 Client
 * Uses region 'auto' and S3v4 signing per Cloudflare R2 specifications.
 */
let r2ClientInstance: S3Client | null = null;

export function getR2Client(): S3Client | null {
  if (!R2_ACCOUNT_ID || !R2_ACCESS_KEY_ID || !R2_SECRET_ACCESS_KEY) {
    return null;
  }

  if (!r2ClientInstance) {
    r2ClientInstance = new S3Client({
      region: 'auto',
      endpoint: `https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
      credentials: {
        accessKeyId: R2_ACCESS_KEY_ID,
        secretAccessKey: R2_SECRET_ACCESS_KEY,
      },
    });
  }

  return r2ClientInstance;
}

export interface PresignedUploadOptions {
  productId: number;
  filename: string;
  mimeType: string;
  sizeBytes?: number;
  expiresInSeconds?: number;
}

export interface PresignedUploadResult {
  upload_url: string;
  http_method: 'PUT';
  required_headers: Record<string, string>;
  storage_key: string;
  public_url: string;
  expires_in_seconds: number;
  is_mock?: boolean;
}

/**
 * Sanitize filename to ensure safe alphanumeric and hyphen characters.
 */
export function sanitizeFilename(filename: string): string {
  const parts = filename.split('.');
  const ext = parts.length > 1 ? `.${parts.pop()?.toLowerCase()}` : '';
  const base = parts.join('.').replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 64);
  return `${base || 'upload'}${ext}`;
}

/**
 * Generate a short-lived presigned PUT URL for direct client upload to Cloudflare R2.
 */
export async function createPresignedUploadUrl(
  options: PresignedUploadOptions
): Promise<PresignedUploadResult> {
  const {
    productId,
    filename,
    mimeType,
    sizeBytes,
    expiresInSeconds = 900,
  } = options;

  const cleanFilename = sanitizeFilename(filename);
  const timestamp = Date.now();
  const randomSuffix = Math.random().toString(36).substring(2, 8);
  const storageKey = `products/${productId}/${timestamp}-${randomSuffix}-${cleanFilename}`;
  const publicUrl = `${R2_PUBLIC_DOMAIN}/${storageKey}`;

  const client = getR2Client();

  if (!client) {
    // Graceful fallback for local development or offline staging rehearsal
    return {
      upload_url: `https://mock-r2.uwearnova.local/${R2_BUCKET_NAME}/${storageKey}?signed=true`,
      http_method: 'PUT',
      required_headers: {
        'Content-Type': mimeType,
      },
      storage_key: storageKey,
      public_url: publicUrl,
      expires_in_seconds: expiresInSeconds,
      is_mock: true,
    };
  }

  const command = new PutObjectCommand({
    Bucket: R2_BUCKET_NAME,
    Key: storageKey,
    ContentType: mimeType,
    ...(sizeBytes ? { ContentLength: sizeBytes } : {}),
  });

  const uploadUrl = await getSignedUrl(client, command, {
    expiresIn: expiresInSeconds,
  });

  return {
    upload_url: uploadUrl,
    http_method: 'PUT',
    required_headers: {
      'Content-Type': mimeType,
    },
    storage_key: storageKey,
    public_url: publicUrl,
    expires_in_seconds: expiresInSeconds,
    is_mock: false,
  };
}

/**
 * Delete an object from Cloudflare R2
 */
export async function deleteR2Object(storageKey: string): Promise<boolean> {
  const client = getR2Client();
  if (!client) {
    return true; // No-op in mock/dev mode
  }

  try {
    const cleanKey = storageKey.replace(/^\/+/, '');
    await client.send(
      new DeleteObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: cleanKey,
      })
    );
    return true;
  } catch (err) {
    console.error('Failed to delete object from Cloudflare R2:', err);
    return false;
  }
}

/**
 * Check if object exists in Cloudflare R2
 */
export async function checkR2ObjectExists(storageKey: string): Promise<boolean> {
  const client = getR2Client();
  if (!client) {
    return false;
  }

  try {
    const cleanKey = storageKey.replace(/^\/+/, '');
    await client.send(
      new HeadObjectCommand({
        Bucket: R2_BUCKET_NAME,
        Key: cleanKey,
      })
    );
    return true;
  } catch {
    return false;
  }
}

/**
 * Resolve public CDN URL from a storage key or existing URL
 */
export function resolvePublicMediaUrl(keyOrUrl: string): string {
  if (!keyOrUrl) return '';
  if (keyOrUrl.startsWith('http://') || keyOrUrl.startsWith('https://')) {
    return keyOrUrl;
  }
  const cleanKey = keyOrUrl.replace(/^\/+/, '');
  return `${R2_PUBLIC_DOMAIN}/${cleanKey}`;
}
