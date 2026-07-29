type AuthUser = { id: string; email: string; name: string; emailVerified: boolean };
export type AuthSession = { user: AuthUser; session: { id: string; expiresAt: string } } | null;

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || body.error?.message || "Authentication failed.");
  return body as T;
}

export function getSession(baseUrl: string) {
  return request<AuthSession>(baseUrl, "/get-session", { method: "GET" });
}

export function signUp(baseUrl: string, details: { email: string; password: string; name: string }) {
  return request<AuthSession>(baseUrl, "/sign-up/email", {
    method: "POST", body: JSON.stringify(details),
  });
}

export function signIn(baseUrl: string, details: { email: string; password: string }) {
  return request<AuthSession>(baseUrl, "/sign-in/email", {
    method: "POST", body: JSON.stringify(details),
  });
}

export function signOut(baseUrl: string) {
  return request<Record<string, unknown>>(baseUrl, "/sign-out", { method: "POST", body: "{}" });
}

export async function getIdentityToken(baseUrl: string): Promise<string> {
  const result = await request<{ token?: string }>(baseUrl, "/token", { method: "GET" });
  if (!result.token) throw new Error("No verified identity token was returned.");
  return result.token;
}
