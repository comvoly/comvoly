export type WorkspaceSummary = {
  id: string; name: string; handle: string; lifecycle: string; role: string;
};

export type WorkspaceDetail = {
  workspace: WorkspaceSummary;
  role: string;
  capabilities: string[];
  setup_steps: Array<{ step_key: string; state: string; completed_at: string | null }>;
  sources: Array<{ id: string; provider: string; display_name: string; state: string; health: string }>;
  imports: Array<{ id: string; source_connection_id: string | null; job_type: string; state: string; stage: string; progress_current: number; progress_total: number | null; warning_count: number; failure_count: number; updated_at: string }>;
};

export type ComvolySession = { account_id: string; workspaces: WorkspaceSummary[] };

export async function api<T>(baseUrl: string, token: string, path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers || {}) },
    });
  } catch {
    throw new Error("Comvoly's service could not be reached. Nothing was uploaded.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Comvoly could not complete that request.");
  return body as T;
}
