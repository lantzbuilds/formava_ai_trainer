import type { RegisterForm, User } from '@/types';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface HealthPayload {
  db: string;
  pgvector: string;
}

/**
 * Base URL for the FastAPI backend.
 *
 * Server-side only. The browser never calls FastAPI directly under the BFF
 * pattern -- it calls Next.js route handlers, which call FastAPI.
 *
 * Deliberately has no default: the "No silent fallbacks" global constraint
 * applies to configuration as well as to data access. systemd supplies this
 * via EnvironmentFile; local development sets it explicitly.
 *
 * Resolved lazily rather than at module load. `next build` imports this module
 * for static analysis, and CI builds without runtime configuration -- a
 * top-level throw would break the build rather than the request. Throwing on
 * first use still fails loudly: the route handler turns it into a 503, which
 * the constraint permits.
 */
function getApiBaseUrl(): string {
  const url = process.env.FORMAVA_API_URL;
  if (!url) {
    throw new Error('FORMAVA_API_URL is not set; refusing to serve');
  }
  return url;
}

class ApiClient {
  async health(): Promise<ApiResponse<HealthPayload>> {
    try {
      const res = await fetch(`${getApiBaseUrl()}/health`, {
        cache: 'no-store',
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        return { success: false, error: body.detail ?? `HTTP ${res.status}` };
      }

      return { success: true, data: (await res.json()) as HealthPayload };
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Unknown error',
      };
    }
  }

  // ---- Auth: implemented in Spec 4 (REST API + Next.js BFF) ----
  // These throw rather than returning a fake success so that any premature
  // use fails loudly. Signatures match the existing calls in AuthContext.

  async login(
    _username: string,
    _password: string
  ): Promise<ApiResponse<{ user: User }>> {
    throw new Error('apiClient.login is not implemented until Spec 4');
  }

  async register(_userData: RegisterForm): Promise<ApiResponse<{ user: User }>> {
    throw new Error('apiClient.register is not implemented until Spec 4');
  }

  async logout(): Promise<void> {
    throw new Error('apiClient.logout is not implemented until Spec 4');
  }
}

export const apiClient = new ApiClient();
