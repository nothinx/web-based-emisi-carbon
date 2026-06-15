// Klien API tipis di atas fetch. Token JWT disuntik dari localStorage.
// Dev: panggilan ke /api/* di-proxy ke backend (lihat vite.config.ts).

import { ApiError as StaticApiError, staticRequest } from "./staticBackend";

const BASE = "/api";
const TOKEN_KEY = "carbon.token";
// Mode statis (GitHub Pages): tanpa backend, engine berjalan di browser.
const STATIC = import.meta.env.VITE_STATIC === "1";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (STATIC) {
    const method = (init.method ?? "GET").toUpperCase();
    const body = init.body ? JSON.parse(init.body as string) : undefined;
    try {
      return await staticRequest<T>(method, path, body);
    } catch (e) {
      if (e instanceof StaticApiError) throw new ApiError(e.status, e.message);
      throw e;
    }
  }
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* abaikan */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),

  async login(email: string, password: string): Promise<string> {
    if (STATIC) return "static-demo";
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch(`${BASE}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    if (!res.ok) throw new ApiError(res.status, "Email atau password salah");
    const data = (await res.json()) as { access_token: string };
    return data.access_token;
  },

  register: (email: string, password: string, full_name?: string) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),
};
