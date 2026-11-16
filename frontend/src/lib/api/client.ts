/**
 * UWEARNOVA Typed Fetch API Client
 * Supports token injection, automatic refresh rotation, guest cart tokens,
 * and unified error extraction.
 */

import { ApiErrorResponse, TokenResponse } from "./types";

export class ApiClientError extends Error {
  status: number;
  code: string;
  details?: any;

  constructor(message: string, status: number, code: string = "API_ERROR", details?: any) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const ACCESS_TOKEN_KEY = "uwearnova_access_token";
const REFRESH_TOKEN_KEY = "uwearnova_refresh_token";
const ANONYMOUS_CART_TOKEN_KEY = "uwearnova_anon_cart_token";

export function getBaseApiUrl(): string {
  if (typeof window === "undefined") {
    return (
      process.env.INTERNAL_API_URL?.replace(/\/+$/, "") ||
      process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ||
      ""
    );
  }
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  return "";
}

// ---------------------------------------------------------------------------
// Token Management
// ---------------------------------------------------------------------------

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return (
      sessionStorage.getItem(ACCESS_TOKEN_KEY) ||
      localStorage.getItem(ACCESS_TOKEN_KEY) ||
      sessionStorage.getItem("uninova_access_token") ||
      localStorage.getItem("uninova_access_token")
    );
  } catch {
    return null;
  }
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY) || localStorage.getItem("uninova_refresh_token");
  } catch {
    return null;
  }
}

export function setTokens(tokens: TokenResponse): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  } catch (e) {
    console.error("Failed to store tokens", e);
  }
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch (e) {
    console.error("Failed to clear tokens", e);
  }
}

export function getAnonymousCartToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(ANONYMOUS_CART_TOKEN_KEY) || localStorage.getItem("uninova_anon_cart_token");
  } catch {
    return null;
  }
}

export function setAnonymousCartToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(ANONYMOUS_CART_TOKEN_KEY, token);
  } catch (e) {
    console.error("Failed to store anonymous cart token", e);
  }
}

export function clearAnonymousCartToken(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(ANONYMOUS_CART_TOKEN_KEY);
  } catch (e) {
    console.error("Failed to clear anonymous cart token", e);
  }
}

// ---------------------------------------------------------------------------
// Core Fetch Wrapper
// ---------------------------------------------------------------------------

interface RequestOptions extends RequestInit {
  params?: Record<string, any>;
  skipAuth?: boolean;
  isRetry?: boolean;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, skipAuth = false, isRetry = false, headers: customHeaders, ...fetchOpts } = options;

  const baseUrl = getBaseApiUrl();
  if (!baseUrl) {
    throw new ApiClientError(
      `FastAPI backend replaced by Supabase data access layer. Endpoint '${endpoint}' should be accessed via direct Supabase API modules.`,
      501,
      "BACKEND_MIGRATED"
    );
  }
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  // Query parameter serialization
  let url = `${baseUrl}${cleanEndpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        if (Array.isArray(value)) {
          value.forEach((v) => searchParams.append(key, String(v)));
        } else {
          searchParams.append(key, String(value));
        }
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(customHeaders as Record<string, string>),
  };

  if (typeof FormData !== "undefined" && fetchOpts.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  // Inject Authorization if token present
  if (!skipAuth) {
    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  // Inject Anonymous Cart Token if guest
  const anonCartToken = getAnonymousCartToken();
  if (anonCartToken) {
    headers["X-Anonymous-Cart-Token"] = anonCartToken;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchOpts,
      headers,
    });
  } catch (err: any) {
    throw new ApiClientError(
      err?.message || "Network error. Please verify your connection to the server.",
      0,
      "NETWORK_ERROR"
    );
  }

  // Save any emitted X-Anonymous-Cart-Token header
  const newAnonToken = response.headers.get("X-Anonymous-Cart-Token");
  if (newAnonToken) {
    setAnonymousCartToken(newAnonToken);
  }

  // Token refresh handling on 401
  if (response.status === 401 && !isRetry && !skipAuth && typeof window !== "undefined") {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        const refreshResp = await fetch(`${baseUrl}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResp.ok) {
          const newTokens: TokenResponse = await refreshResp.json();
          setTokens(newTokens);
          // Retry original request
          return apiClient<T>(endpoint, { ...options, isRetry: true });
        } else {
          clearTokens();
        }
      } catch {
        clearTokens();
      }
    }
  }

  // Handle error responses
  if (!response.ok) {
    let errorData: ApiErrorResponse | null = null;
    try {
      errorData = await response.json();
    } catch {
      // response is not json
    }

    let message = "An unexpected error occurred.";
    let code = "UNKNOWN_ERROR";
    let details: any = undefined;

    if (errorData?.error) {
      message = errorData.error.message || message;
      code = errorData.error.code || code;
      details = errorData.error.details;
    } else if (typeof errorData?.detail === "string") {
      message = errorData.detail;
      code = "VALIDATION_OR_AUTH_ERROR";
    } else if (Array.isArray(errorData?.detail)) {
      message = errorData.detail.map((d) => d.msg).join(", ");
      code = "VALIDATION_ERROR";
      details = errorData.detail;
    } else {
      message = response.statusText || `HTTP ${response.status} error`;
      code = `HTTP_${response.status}`;
    }

    throw new ApiClientError(message, response.status, code, details);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
