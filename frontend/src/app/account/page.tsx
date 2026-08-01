"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, ComvolySession, WorkspaceDetail, WorkspaceSummary } from "@/lib/comvoly-api";
import { AuthSession, getIdentityToken, getSession, signIn, signOut, signUp } from "@/lib/neon-auth";
import { streamTelegramExport, telegramFileFingerprint, TelegramStreamSummary } from "@/lib/telegram-stream";

const AUTH_URL = process.env.NEXT_PUBLIC_NEON_AUTH_URL;
const API_URL = process.env.NEXT_PUBLIC_COMVOLY_API_URL || "https://api.comvoly.com";

type TelegramPreview = {
  parser_version: string; external_community_id: string; community_name: string; export_type: string;
  message_count: number; service_event_count: number; participant_count: number; media_count: number;
  history_start: string | null; history_end: string | null; warnings: string[];
};

type TelegramLiveStatus = {
  source_id: string; state: string; configured: boolean; bot_username?: string;
  membership_status?: string; receives_messages?: boolean; last_received_at?: string | null;
  install_url?: string; webhook_url?: string; connection_prepared_at?: string;
  connection_expired?: boolean;
};

type IntelligenceAnswer = {
  question: string; answer: string; evidence_count: number; mode: string;
  citations: Array<{ content_id: string; source_name: string; provider: string;
    external_item_id: string; author: string; source_created_at: string; excerpt: string;
    ingestion_method: string }>;
};

type ImportReview = TelegramImportStatus & {
  summary: Partial<TelegramStreamSummary> & { warnings?: string[] };
  inventory: { message_count: number; total_count: number; excluded_count: number; participant_count: number;
    overlap_count: number; history_start: string | null; history_end: string | null };
  diagnostics: { new: number; unchanged: number; changed: number; skipped: number };
  policy: { date_from: string | null; date_to: string | null; excluded_author_ids: string[] };
  samples: Array<{ id: string; external_item_id: string; author_external_id: string | null;
    author_display_name: string | null; body_text: string | null; source_created_at: string; review_state: string }>;
  can_accept: boolean; can_cancel: boolean; can_restart: boolean;
};

type IngestionSource = {
  id: string; provider: string; display_name: string; state: string; health: string;
  receives_messages?: boolean; last_received_at?: string | null; stored_message_count: number;
  live_message_count: number; historical_message_count: number; history_start?: string | null;
  history_end?: string | null; last_ingested_at?: string | null;
};
type IngestionHealth = { workspace_id: string; stored_message_count: number; last_ingested_at: string | null; sources: IngestionSource[] };
type TelegramImportStatus = {
  job_id: string; source_id: string; state: string; stage: string; progress_current: number;
  progress_total: number | null; bytes_current: number; bytes_total: number | null;
  completed_chunks: number[]; warning_count: number; failure_count: number; attempt: number; resumed?: boolean;
};

export default function AccountPage() {
  if (!AUTH_URL) return <Shell><h1 className="text-3xl font-semibold">Development sign-in is not configured</h1><p className="mt-4 text-slate-400">Production access remains unchanged.</p></Shell>;
  return <ConfiguredAccount authUrl={AUTH_URL} />;
}

function ConfiguredAccount({ authUrl }: { authUrl: string }) {
  const [authSession, setAuthSession] = useState<AuthSession>(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [token, setToken] = useState("");
  const [session, setSession] = useState<ComvolySession | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<WorkspaceDetail | null>(null);

  const refreshSession = useCallback(async () => {
    const identityToken = await getIdentityToken(authUrl);
    const body = await api<ComvolySession>(API_URL, identityToken, "/v2/session");
    setToken(identityToken);
    setSession(body);
    setSelectedId((current) => body.workspaces.some((item) => item.id === current)
      ? current : body.workspaces[0]?.id || "");
    return body;
  }, [authUrl]);

  useEffect(() => {
    let cancelled = false;
    getSession(authUrl).then((value) => { if (!cancelled) setAuthSession(value); })
      .catch(() => undefined).finally(() => !cancelled && setChecking(false));
    return () => { cancelled = true; };
  }, [authUrl]);

  useEffect(() => {
    if (!authSession?.user) return;
    const timer = window.setTimeout(() => {
      refreshSession().catch((error: Error) => setMessage(error.message));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [authSession?.user, refreshSession]);

  useEffect(() => {
    if (!selectedId || !token) return;
    api<WorkspaceDetail>(API_URL, token, `/v2/workspaces/${selectedId}`)
      .then(setDetail).catch((error: Error) => setMessage(error.message));
  }, [selectedId, token]);

  useEffect(() => {
    if (!token || typeof window === "undefined") return;
    const invite = new URLSearchParams(window.location.search).get("invite");
    if (!invite) return;
    api<{ workspace_id: string }>(API_URL, token, "/v2/invitations/accept", {
      method: "POST", body: JSON.stringify({ token: invite }),
    }).then(async ({ workspace_id }) => {
      await refreshSession(); setSelectedId(workspace_id); setMessage("Invitation accepted. Welcome to the community.");
      window.history.replaceState({}, "", "/account");
    }).catch((error: Error) => setMessage(error.message));
  }, [token, refreshSession]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setMessage("");
    try {
      await (mode === "sign-up" ? signUp(authUrl, { email, password, name: name || email.split("@")[0] }) : signIn(authUrl, { email, password }));
      setAuthSession(await getSession(authUrl));
    } catch (error) { setMessage(error instanceof Error ? error.message : "Authentication failed."); }
  }

  if (checking) return <Shell><p className="text-slate-300">Checking your account…</p></Shell>;
  if (!authSession?.user) return <Shell>
    <Eyebrow>Comvoly account</Eyebrow>
    <h1 className="mt-3 text-4xl font-semibold">{mode === "sign-up" ? "Create your account" : "Welcome back"}</h1>
    <p className="mt-3 max-w-xl leading-7 text-slate-400">One sign-in for every community you own or join. Knowledge remains private until an owner invites or approves you.</p>
    <form onSubmit={submit} className="mt-8 max-w-md space-y-4">
      {mode === "sign-up" && <Field label="Name" value={name} setValue={setName} autoComplete="name" />}
      <Field label="Email" value={email} setValue={setEmail} type="email" autoComplete="email" />
      <Field label="Password" value={password} setValue={setPassword} type="password" autoComplete={mode === "sign-up" ? "new-password" : "current-password"} />
      {message && <Notice>{message}</Notice>}
      <Primary>{mode === "sign-up" ? "Create account" : "Sign in"}</Primary>
    </form>
    <button onClick={() => { setMode(mode === "sign-in" ? "sign-up" : "sign-in"); setMessage(""); }} className="mt-5 text-sm text-slate-300 underline underline-offset-4">{mode === "sign-in" ? "New to Comvoly? Create an account" : "Already have an account? Sign in"}</button>
  </Shell>;

  return <Shell wide>
    <header className="flex flex-wrap items-start justify-between gap-5">
      <div><Eyebrow>Your Comvoly account</Eyebrow><h1 className="mt-3 text-3xl font-semibold">Welcome, {authSession.user.name}</h1><p className="mt-2 text-slate-400">One account. Every authorised community.</p></div>
      <button onClick={async () => { await signOut(authUrl); setAuthSession(null); setSession(null); }} className="rounded-xl border border-white/15 px-4 py-2 text-sm">Sign out</button>
    </header>
    {message && <Notice>{message}</Notice>}
    {!session && !message && <p className="mt-8 text-slate-300">Loading your communities…</p>}
    {session && <AccountHome session={session} selectedId={selectedId} select={setSelectedId} detail={detail} token={token}
      refresh={async () => { const next = await refreshSession(); const target = next.workspaces.some((item) => item.id === selectedId) ? selectedId : next.workspaces[0]?.id || ""; if (target) setDetail(await api<WorkspaceDetail>(API_URL, token, `/v2/workspaces/${target}`)); else setDetail(null); }}
      onDeleted={async () => { setDetail(null); setSelectedId(""); await refreshSession(); }} setMessage={setMessage} />}
  </Shell>;
}

function AccountHome({ session, selectedId, select, detail, token, refresh, onDeleted, setMessage }: {
  session: ComvolySession; selectedId: string; select: (id: string) => void; detail: WorkspaceDetail | null;
  token: string; refresh: () => Promise<void>; onDeleted: () => Promise<void>; setMessage: (value: string) => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  return <div className="mt-9 grid gap-6 lg:grid-cols-[17rem_1fr]">
    <aside className="rounded-3xl border border-white/10 bg-white/[.025] p-4">
      <div className="flex items-center justify-between px-2"><h2 className="font-semibold">Communities</h2><button onClick={() => setShowCreate(!showCreate)} className="rounded-lg bg-[#ffcf4a] px-3 py-1.5 text-sm font-bold text-[#07152b]">New</button></div>
      {showCreate && <CreateWorkspace token={token} onCreated={async (id) => { await refresh(); select(id); setShowCreate(false); }} />}
      <div className="mt-4 space-y-2">{session.workspaces.map((workspace) => <WorkspaceButton key={workspace.id} workspace={workspace} selected={selectedId === workspace.id} onClick={() => select(workspace.id)} />)}</div>
      {!session.workspaces.length && <p className="mt-5 px-2 text-sm leading-6 text-slate-400">No communities yet. Create one as an owner or follow an invitation from another owner.</p>}
    </aside>
    <section>{selectedId ? (detail ? <WorkspacePanel detail={detail} token={token} refresh={refresh} onDeleted={onDeleted} setMessage={setMessage} /> : <p className="text-slate-300">Opening community…</p>) : <EmptyState />}</section>
  </div>;
}

function CreateWorkspace({ token, onCreated }: { token: string; onCreated: (id: string) => Promise<void> }) {
  const [name, setName] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const handle = useMemo(() => name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48), [name]);
  return <form className="mt-4 rounded-2xl border border-white/10 bg-[#061124] p-3" onSubmit={async (event) => { event.preventDefault(); setBusy(true); setError(""); try { const result = await api<{ workspace_id: string }>(API_URL, token, "/v2/workspaces", { method: "POST", body: JSON.stringify({ name, handle }) }); await onCreated(result.workspace_id); } catch (e) { setError(e instanceof Error ? e.message : "Could not create community."); } finally { setBusy(false); } }}>
    <label className="text-xs text-slate-400">Community name<input required value={name} onChange={(e) => setName(e.target.value)} className="mt-2 w-full rounded-lg border border-white/15 bg-[#07152d] px-3 py-2 text-sm text-white" /></label>
    <p className="mt-2 truncate text-xs text-slate-500">comvoly / {handle || "community"}</p>{error && <p className="mt-2 text-xs text-rose-300">{error}</p>}
    <button disabled={busy} className="mt-3 w-full rounded-lg border border-[#ffcf4a]/40 px-3 py-2 text-xs font-semibold text-[#ffcf4a]">{busy ? "Creating…" : "Create workspace"}</button>
  </form>;
}

function WorkspacePanel({ detail, token, refresh, onDeleted, setMessage }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void>; onDeleted: () => Promise<void>; setMessage: (value: string) => void }) {
  const ownerTools = detail.capabilities.includes("manage_sources");
  const completed = detail.setup_steps.filter((step) => step.state === "completed").length;
  return <div className="space-y-6">
    <div className="rounded-3xl border border-white/10 bg-white/[.035] p-6"><Eyebrow>{detail.role}</Eyebrow><h2 className="mt-2 text-3xl font-semibold">{detail.workspace.name}</h2><p className="mt-2 text-slate-400">{detail.workspace.lifecycle === "setup" ? "Setting up community intelligence" : detail.workspace.lifecycle}</p></div>
    {ownerTools && <div className="rounded-3xl border border-[#ffcf4a]/20 bg-[#ffcf4a]/[.04] p-6"><div className="flex items-center justify-between gap-4"><div><h3 className="text-lg font-semibold">Owner setup</h3><p className="mt-1 text-sm text-slate-400">{completed} of {detail.setup_steps.length} steps complete</p></div><span className="text-2xl font-bold text-[#ffcf4a]">{detail.setup_steps.length ? Math.round(completed / detail.setup_steps.length * 100) : 0}%</span></div><div className="mt-5 space-y-2">{detail.setup_steps.map((step) => <SetupStep key={step.step_key} step={step} workspaceId={detail.workspace.id} token={token} refresh={refresh} />)}</div></div>}
    <WorkspaceIntelligencePanel detail={detail} token={token} />
    {ownerTools && <IngestionHealthPanel detail={detail} token={token} />}
    <Sources detail={detail} token={token} refresh={refresh} />
    {detail.capabilities.includes("invite_members") && <Invite workspaceId={detail.workspace.id} token={token} setMessage={setMessage} refresh={refresh} />}
    {detail.capabilities.includes("delete_workspace") && <DeleteCommunity detail={detail} token={token} onDeleted={onDeleted} setMessage={setMessage} />}
  </div>;
}

const stepLabels: Record<string, string> = { community_details: "Confirm community details", connect_source: "Plan a platform connection", import_history: "Import historical knowledge", review_knowledge: "Review imported knowledge", invite_members: "Invite your first member" };
function SetupStep({ step, workspaceId, token, refresh }: { step: WorkspaceDetail["setup_steps"][number]; workspaceId: string; token: string; refresh: () => Promise<void> }) {
  return <div className="flex items-center justify-between gap-3 rounded-xl bg-white/[.035] px-4 py-3"><div><p className="text-sm font-medium">{stepLabels[step.step_key] || step.step_key}</p><p className="mt-1 text-xs capitalize text-slate-500">{step.state.replace("_", " ")}</p></div>{step.state !== "completed" && <button onClick={async () => { await api(API_URL, token, `/v2/workspaces/${workspaceId}/setup/${step.step_key}`, { method: "POST", body: JSON.stringify({ state: "completed" }) }); await refresh(); }} className="text-xs font-semibold text-[#ffcf4a]">Mark done</button>}</div>;
}

function IngestionHealthPanel({ detail, token }: { detail: WorkspaceDetail; token: string }) {
  const [health, setHealth] = useState<IngestionHealth | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      setHealth(await api<IngestionHealth>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/ingestion`));
      setError("");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load ingestion status."); }
  }, [detail.workspace.id, token]);
  useEffect(() => {
    const initial = window.setTimeout(() => void load(), 0);
    const timer = window.setInterval(() => void load(), 10000);
    return () => { window.clearTimeout(initial); window.clearInterval(timer); };
  }, [load]);
  return <div className="rounded-3xl border border-white/10 bg-white/[.035] p-6">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><Eyebrow>Knowledge ingestion</Eyebrow><h3 className="mt-2 text-xl font-semibold">Is Comvoly receiving messages?</h3><p className="mt-2 text-sm text-slate-400">This updates automatically every 10 seconds.</p></div>{health && <div className="text-right"><p className="text-2xl font-semibold">{health.stored_message_count.toLocaleString()}</p><p className="text-xs text-slate-500">messages stored</p></div>}</div>
    {error && <p className="mt-4 text-sm text-rose-200">{error}</p>}
    {!health && !error && <p className="mt-4 text-sm text-slate-400">Checking ingestion status…</p>}
    <div className="mt-5 space-y-3">{health?.sources.map((source) => {
      const live = source.state === "connected" && source.receives_messages;
      const connecting = source.state === "connecting";
      return <div key={source.id} className="rounded-2xl border border-white/10 bg-[#061124] p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold">{source.display_name}</p><p className="mt-1 text-xs capitalize text-slate-500">{source.provider}</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${live ? "bg-emerald-400/10 text-emerald-200" : connecting ? "bg-amber-300/10 text-amber-100" : "bg-rose-300/10 text-rose-200"}`}>{live ? "Receiving messages" : connecting ? "Connecting" : "Needs attention"}</span></div><div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Live messages" value={source.live_message_count} /><Metric label="Imported history" value={source.historical_message_count} /><Metric label="All stored" value={source.stored_message_count} /><div className="rounded-xl bg-white/[.04] p-3"><p className="text-sm font-semibold">{formatDateTime(source.last_ingested_at || null)}</p><p className="mt-1 text-xs text-slate-500">Last received</p></div></div>{source.historical_message_count > 0 && <p className="mt-3 text-xs text-slate-500">Historical coverage: {formatDate(source.history_start || null)} – {formatDate(source.history_end || null)}</p>}</div>;
    })}</div>
  </div>;
}

function Sources({ detail, token, refresh }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void> }) {
  const canManage = detail.capabilities.includes("manage_sources");
  return <div className="rounded-3xl border border-white/10 bg-white/[.035] p-6"><h3 className="text-lg font-semibold">Connect your community</h3><p className="mt-2 text-sm leading-6 text-slate-400">Add Comvoly to your Telegram group. New messages will become part of its private community knowledge.</p>
    {canManage && <TelegramConnectWizard detail={detail} token={token} refresh={refresh} />}
    <div className="mt-5 space-y-3">{detail.sources.map((source) => <div key={source.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 px-4 py-3"><div><p className="font-medium">{source.display_name}</p><p className="mt-1 text-xs capitalize text-slate-500">{source.provider} · {source.state}</p></div><div className="flex items-center gap-3"><span className={`rounded-full px-3 py-1 text-xs ${source.state === "connected" ? "bg-emerald-400/10 text-emerald-200" : "bg-slate-700"}`}>{source.state === "connected" ? "Connected" : "Not connected"}</span>{canManage && source.provider === "telegram" && <button onClick={async () => { if (!window.confirm("Remove this Telegram connection? Stored messages will be kept.")) return; await api(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/disconnect/${source.id}`, { method: "POST", body: "{}" }); await refresh(); }} className="text-xs font-semibold text-rose-200 underline underline-offset-4">Remove connection</button>}</div></div>)}{!detail.sources.length && <p className="text-sm text-slate-500">No active connections yet.</p>}</div>
    {canManage && <details className="mt-7 border-t border-white/10 pt-5"><summary className="cursor-pointer font-medium text-slate-200">Add earlier Telegram messages <span className="text-sm font-normal text-slate-500">(optional)</span></summary><TelegramHistoryImport detail={detail} token={token} refresh={refresh} /></details>}
    <details className="mt-5 text-sm text-slate-400"><summary className="cursor-pointer">Other platforms</summary><p className="mt-3 leading-6">Discord and Skool connections are planned after the Telegram pilot.</p></details>
    <ImportReviewList detail={detail} token={token} refresh={refresh} />
  </div>;
}

function ImportReviewList({ detail, token, refresh }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void> }) {
  const [openId, setOpenId] = useState("");
  const [review, setReview] = useState<ImportReview | null>(null);
  const [busyAction, setBusyAction] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [excludedSenders, setExcludedSenders] = useState("");

  async function load(jobId: string) {
    if (openId === jobId) { setOpenId(""); setReview(null); return; }
    setOpenId(jobId); setReview(null); setError(""); setMessage("");
    try {
      const next = await api<ImportReview>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/imports/${jobId}/review`);
      setReview(next); setDateFrom(next.policy.date_from || ""); setDateTo(next.policy.date_to || "");
      setExcludedSenders(next.policy.excluded_author_ids.join(", "));
    }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load this import review."); }
  }
  async function action(name: "accept" | "cancel" | "restart") {
    if (!review) return;
    if (name === "cancel" && !window.confirm("Cancel this import and remove only its staged historical messages? Live Telegram messages will remain.")) return;
    setBusyAction(name); setError(""); setMessage("");
    try {
      const next = await api<ImportReview | TelegramImportStatus>(API_URL, token,
        `/v2/workspaces/${detail.workspace.id}/telegram/imports/${review.job_id}/${name}`, { method: "POST", body: "{}" });
      if (name === "restart") {
        setReview(null); setOpenId(""); setMessage("Restart prepared. Choose the same result.json above to resume from the beginning.");
      } else setReview(next as ImportReview);
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : `Could not ${name} this import.`); }
    finally { setBusyAction(""); }
  }
  async function applyPolicy() {
    if (!review) return;
    setBusyAction("policy"); setError(""); setMessage("");
    try {
      const next = await api<ImportReview>(API_URL, token,
        `/v2/workspaces/${detail.workspace.id}/telegram/imports/${review.job_id}/policy`, {
          method: "POST", body: JSON.stringify({ date_from: dateFrom || null, date_to: dateTo || null,
            excluded_author_ids: excludedSenders.split(",").map((value) => value.trim()).filter(Boolean) }),
        });
      setReview(next); setMessage(`${next.inventory.message_count.toLocaleString()} messages included; ${next.inventory.excluded_count.toLocaleString()} excluded.`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not apply the review policy."); }
    finally { setBusyAction(""); }
  }
  function downloadDiagnostics() {
    if (!review) return;
    const report = { generated_at: new Date().toISOString(), workspace: detail.workspace.name,
      import_job_id: review.job_id, state: review.state, inventory: review.inventory,
      diagnostics: review.diagnostics, policy: review.policy, warnings: review.summary.warnings || [] };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = `comvoly-import-${review.job_id}-diagnostics.json`;
    link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="mt-6 border-t border-white/10 pt-5"><div className="flex flex-wrap items-end justify-between gap-3"><div><h4 className="font-medium">Historical import review</h4><p className="mt-1 text-xs text-slate-500">Imported knowledge is not used in answers until you accept it.</p></div></div>
    {message && <p className="mt-3 rounded-xl bg-emerald-300/10 p-3 text-sm text-emerald-100">{message}</p>}
    {detail.imports.length ? detail.imports.map((job) => <div key={job.id} className="mt-3 rounded-xl border border-white/10 bg-[#061124] p-4 text-sm text-slate-300"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-medium capitalize">{job.stage.replaceAll("_", " ")}</p><p className="mt-1 text-xs text-slate-500">{job.progress_current.toLocaleString()}/{job.progress_total?.toLocaleString() ?? "?"} messages · updated {formatDateTime(job.updated_at)}</p></div><button onClick={() => void load(job.id)} className="rounded-lg border border-white/15 px-3 py-2 text-xs font-semibold">{openId === job.id ? "Close" : job.state === "owner_review" ? "Review and accept" : "View details"}</button></div>{job.warning_count + job.failure_count > 0 && <p className="mt-2 text-xs text-amber-200">{job.warning_count} warnings · {job.failure_count} failures</p>}
      {openId === job.id && !review && !error && <p className="mt-4 text-xs text-slate-400">Loading review…</p>}
      {openId === job.id && error && <p className="mt-4 text-sm text-rose-200">{error}</p>}
      {openId === job.id && review && <div className="mt-4 border-t border-white/10 pt-4"><div className="grid grid-cols-2 gap-3 sm:grid-cols-5"><Metric label="Messages staged" value={review.inventory.message_count} /><Metric label="Already stored" value={review.inventory.overlap_count} /><Metric label="Participants" value={review.inventory.participant_count} /><Metric label="Warnings" value={review.warning_count} /><Metric label="Failed items" value={review.failure_count} /></div><p className="mt-3 text-xs text-slate-500">Coverage: {formatDate(review.inventory.history_start)} – {formatDate(review.inventory.history_end)}</p>{(review.summary.warnings || []).map((warning) => <p key={warning} className="mt-2 rounded-lg bg-amber-300/10 p-2 text-xs text-amber-100">{warning}</p>)}{review.samples.length > 0 && <div className="mt-4"><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recent sample</p><div className="mt-2 space-y-2">{review.samples.map((sample) => <div key={sample.id} className="rounded-lg bg-white/[.04] p-3"><div className="flex justify-between gap-3 text-xs text-slate-500"><span>{sample.author_display_name || sample.author_external_id || "Community member"}</span><span>{formatDate(sample.source_created_at)}</span></div><p className="mt-1 line-clamp-3 text-sm text-slate-300">{sample.body_text || "Message without text"}</p></div>)}</div></div>}<div className="mt-5 flex flex-wrap gap-3">{review.can_accept && <button disabled={Boolean(busyAction)} onClick={() => void action("accept")} className="rounded-xl bg-[#ffcf4a] px-4 py-2.5 font-bold text-[#07152b]">{busyAction === "accept" ? "Accepting…" : "Accept knowledge"}</button>}{review.can_cancel && <button disabled={Boolean(busyAction)} onClick={() => void action("cancel")} className="rounded-xl border border-rose-300/30 px-4 py-2.5 font-semibold text-rose-200">{busyAction === "cancel" ? "Cancelling…" : "Cancel import"}</button>}{review.can_restart && <button disabled={Boolean(busyAction)} onClick={() => void action("restart")} className="rounded-xl border border-[#ffcf4a]/40 px-4 py-2.5 font-semibold text-[#ffcf4a]">{busyAction === "restart" ? "Preparing…" : "Restart import"}</button>}{review.state === "active" && <span className="rounded-full bg-emerald-400/10 px-3 py-2 text-xs font-semibold text-emerald-200">Accepted · available to Comvoly</span>}{review.state === "cancelled" && <span className="rounded-full bg-slate-700 px-3 py-2 text-xs">Cancelled · staged messages removed</span>}</div></div>}
      {openId === job.id && review && <ReviewCurationPanel review={review} busy={Boolean(busyAction)}
        dateFrom={dateFrom} dateTo={dateTo} excludedSenders={excludedSenders}
        setDateFrom={setDateFrom} setDateTo={setDateTo} setExcludedSenders={setExcludedSenders}
        applyPolicy={applyPolicy} downloadDiagnostics={downloadDiagnostics} />}
    </div>) : <p className="mt-2 text-sm text-slate-500">No historical imports yet.</p>}
  </div>;
}

function ReviewCurationPanel({ review, busy, dateFrom, dateTo, excludedSenders, setDateFrom, setDateTo,
  setExcludedSenders, applyPolicy, downloadDiagnostics }: { review: ImportReview; busy: boolean;
  dateFrom: string; dateTo: string; excludedSenders: string; setDateFrom: (value: string) => void;
  setDateTo: (value: string) => void; setExcludedSenders: (value: string) => void;
  applyPolicy: () => Promise<void>; downloadDiagnostics: () => void }) {
  return <div className="mt-4 rounded-xl border border-white/10 bg-white/[.025] p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold">Import diagnostics</p><p className="mt-1 text-xs text-slate-500">What this export would add or change.</p></div><button onClick={downloadDiagnostics} className="rounded-lg border border-white/15 px-3 py-2 text-xs font-semibold">Download report</button></div><div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="New" value={review.diagnostics.new} /><Metric label="Already identical" value={review.diagnostics.unchanged} /><Metric label="Changed versions" value={review.diagnostics.changed} /><Metric label="Skipped events" value={review.diagnostics.skipped} /></div>
    {review.can_accept && <div className="mt-5 border-t border-white/10 pt-4"><p className="font-semibold">Choose included knowledge</p><p className="mt-1 text-xs leading-5 text-slate-500">Filters are reversible until acceptance. Excluded messages remain unavailable to Comvoly.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-xs text-slate-400">From date<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1 w-full rounded-lg border border-white/15 bg-[#091a36] px-3 py-2 text-sm text-white" /></label><label className="text-xs text-slate-400">To date<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1 w-full rounded-lg border border-white/15 bg-[#091a36] px-3 py-2 text-sm text-white" /></label></div><label className="mt-3 block text-xs text-slate-400">Exclude sender IDs <span className="text-slate-600">(comma-separated)</span><input value={excludedSenders} onChange={(event) => setExcludedSenders(event.target.value)} placeholder="user123, user456" className="mt-1 w-full rounded-lg border border-white/15 bg-[#091a36] px-3 py-2 text-sm text-white" /></label><div className="mt-4 flex flex-wrap items-center gap-3"><button disabled={busy} onClick={() => void applyPolicy()} className="rounded-xl border border-[#ffcf4a]/40 px-4 py-2.5 font-semibold text-[#ffcf4a]">{busy ? "Applying…" : "Apply filters"}</button><span className="text-xs text-slate-500">{review.inventory.message_count.toLocaleString()} included · {review.inventory.excluded_count.toLocaleString()} excluded</span></div></div>}
  </div>;
}

function TelegramConnectWizard({ detail, token, refresh }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void> }) {
  const source = detail.sources.find((item) => item.provider === "telegram");
  const [name, setName] = useState(source?.display_name || "");
  const [status, setStatus] = useState<TelegramLiveStatus | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const expired = Boolean(status?.connection_expired);
  const load = useCallback(async () => {
    if (!source?.id) return;
    const next = await api<TelegramLiveStatus>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/live/status/${source.id}`);
    setStatus(next); if (next.state === "connected" && source.state !== "connected") await refresh();
  }, [detail.workspace.id, refresh, source, token]);
  useEffect(() => {
    if (!source?.id || status?.state === "connected" || expired) return;
    const initial = window.setTimeout(() => void load().catch((e: Error) => setError(e.message)), 0);
    const timer = window.setInterval(() => void load().catch(() => undefined), 4000);
    return () => { window.clearTimeout(initial); window.clearInterval(timer); };
  }, [expired, load, source?.id, status?.state]);
  async function connect() {
    setBusy(true); setError("");
    try {
      setStatus(await api<TelegramLiveStatus>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/connect`, { method: "POST", body: JSON.stringify({ display_name: name }) }));
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not start the Telegram connection."); }
    finally { setBusy(false); }
  }
  const connected = source?.state === "connected" || status?.state === "connected";
  return <div className="mt-6 rounded-2xl border border-[#ffcf4a]/25 bg-[#061124] p-5">
    {connected ? <div className="flex items-start gap-3"><span className="mt-1 h-3 w-3 rounded-full bg-emerald-400" /><div><p className="font-semibold text-emerald-200">Telegram connected</p><p className="mt-1 text-sm text-slate-400">New messages are arriving automatically.</p></div></div> : <>
      <p className="font-semibold">Connect Telegram</p><p className="mt-1 text-sm text-slate-400">Comvoly will wait for Telegram to confirm that the bot was added to your group.</p>
      {expired && <p className="mt-4 rounded-xl bg-amber-300/10 p-3 text-sm text-amber-100">Telegram did not confirm the previous attempt within 10 minutes. It is safe to create a fresh connection.</p>}
      {(!status?.install_url || expired) && <div className="mt-4 flex flex-col gap-3 sm:flex-row"><input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} placeholder="Telegram group name" className="flex-1 rounded-xl border border-white/15 bg-[#091a36] px-4 py-3 text-sm" /><button disabled={busy || !name.trim()} onClick={connect} className="rounded-xl bg-[#ffcf4a] px-5 py-3 font-bold text-[#07152b] disabled:opacity-50">{busy ? "Getting ready…" : source ? "Try a new connection" : "Connect Telegram"}</button></div>}
      {status?.install_url && !expired && <div className="mt-4"><a href={status.install_url} target="_blank" rel="noreferrer" className="inline-flex rounded-xl bg-[#ffcf4a] px-5 py-3 font-bold text-[#07152b]">Open Telegram and choose the group</a><ol className="mt-4 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-400"><li>On Telegram&apos;s launch page, press <strong className="text-slate-200">Open Telegram</strong>.</li><li>Select the intended group and confirm adding ComvolyBot.</li><li>Return here. Comvoly will first confirm the bot, then ask for a test message.</li></ol></div>}
      {source && status && !status.install_url && !connected && !expired && <p className="mt-3 text-xs text-slate-500">Telegram has not confirmed this connection yet. If you closed its launch page, create a fresh connection.</p>}
    </>}{error && <p className="mt-3 text-sm text-rose-200">{error}</p>}
  </div>;
}

/** @deprecated Retained temporarily as a compatibility reference for the pre-streaming pilot. */
export function LegacyTelegramHistoryImport({ detail, token, refresh }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void> }) {
  const [document, setDocument] = useState<Record<string, unknown> | null>(null);
  const [preview, setPreview] = useState<TelegramPreview | null>(null);
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const telegramSource = detail.sources.find((source) => source.provider === "telegram");

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(""); setPreview(null); setDocument(null); setFileName(file.name);
    if (file.size > 25 * 1024 * 1024) { setError("This browser pilot accepts result.json files up to 25 MB."); return; }
    try {
      const parsed = JSON.parse(await file.text()) as Record<string, unknown>;
      const result = await api<TelegramPreview>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/preview`, {
        method: "POST", body: JSON.stringify({ export: parsed }),
      });
      setDocument(parsed); setPreview(result);
    } catch (e) { setError(e instanceof Error ? e.message : "That Telegram export could not be read."); }
  }

  async function importHistory() {
    if (!document || !preview || !Array.isArray(document.messages)) return;
    setBusy(true); setError(""); setProgress(0);
    try {
      const started = await api<{ job_id: string; source_id: string }>(API_URL, token,
        `/v2/workspaces/${detail.workspace.id}/telegram/imports`, {
          method: "POST", body: JSON.stringify({ summary: preview, source_id: telegramSource?.id,
            idempotency_key: `browser-${crypto.randomUUID()}` }),
        });
      const chunks: unknown[][] = [];
      for (let index = 0; index < document.messages.length; index += 200) chunks.push(document.messages.slice(index, index + 200));
      for (let index = 0; index < chunks.length; index += 1) {
        const result = await api<{ progress_current: number }>(API_URL, token,
          `/v2/workspaces/${detail.workspace.id}/telegram/imports/${started.job_id}/chunks`, {
            method: "POST", body: JSON.stringify({ chunk_index: index, messages: chunks[index] }),
          });
        setProgress(result.progress_current);
      }
      await api(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/imports/${started.job_id}/complete`, { method: "POST", body: "{}" });
      setProgress(preview.message_count); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "The import stopped safely and can be retried."); }
    finally { setBusy(false); }
  }

  return <div className="mt-7 border-t border-white/10 pt-6">
    <Eyebrow>Telegram history</Eyebrow><h4 className="mt-2 text-lg font-semibold">Import the knowledge from before the bot joins</h4>
    <p className="mt-2 text-sm leading-6 text-slate-400">In Telegram Desktop, export the intended group as machine-readable JSON and select its <code className="text-slate-300">result.json</code>. Comvoly inventories it before storing messages. Media files are counted but are not uploaded in this milestone.</p>
    <label className="mt-4 block cursor-pointer rounded-2xl border border-dashed border-white/20 bg-[#061124] p-5 text-center text-sm hover:border-[#ffcf4a]/60"><span className="font-semibold text-[#ffcf4a]">Choose Telegram result.json</span><input type="file" accept="application/json,.json" onChange={chooseFile} className="sr-only" /></label>
    {fileName && <p className="mt-2 text-xs text-slate-500">Selected: {fileName}</p>}{error && <p className="mt-3 rounded-xl bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
    {preview && <div className="mt-5 rounded-2xl border border-white/10 bg-[#061124] p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold">{preview.community_name}</p><p className="mt-1 text-xs text-slate-500">{preview.export_type} · {preview.parser_version}</p></div><span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs text-emerald-200">Preview ready</span></div><div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Messages" value={preview.message_count} /><Metric label="People" value={preview.participant_count} /><Metric label="Media refs" value={preview.media_count} /><Metric label="Service events" value={preview.service_event_count} /></div><p className="mt-4 text-xs text-slate-500">{formatDate(preview.history_start)} – {formatDate(preview.history_end)}</p>{preview.warnings.map((warning) => <p key={warning} className="mt-2 text-xs text-amber-200">{warning}</p>)}<button disabled={busy} onClick={importHistory} className="mt-5 w-full rounded-xl bg-[#ffcf4a] px-4 py-3 font-bold text-[#07152b]">{busy ? `Importing ${progress}/${preview.message_count}…` : progress === preview.message_count && progress > 0 ? "Imported — ready for review" : `Import ${preview.message_count} messages`}</button></div>}
  </div>;
}

function TelegramHistoryImport({ detail, token, refresh }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void> }) {
  const [file, setFile] = useState<File | null>(null);
  const [summary, setSummary] = useState<TelegramStreamSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState("");
  const [bytesRead, setBytesRead] = useState(0);
  const [messagesRead, setMessagesRead] = useState(0);
  const [stored, setStored] = useState(0);
  const [wasResumed, setWasResumed] = useState(false);
  const [error, setError] = useState("");
  const telegramSource = detail.sources.find((source) => source.provider === "telegram");

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] || null;
    setError(""); setSummary(null); setStage(""); setBytesRead(0); setMessagesRead(0); setStored(0); setWasResumed(false);
    if (selected && selected.size > 4 * 1024 * 1024 * 1024) {
      setFile(null); setError("Choose Telegram's result.json file up to the 4 GB export ceiling."); return;
    }
    setFile(selected);
  }

  async function importHistory() {
    if (!file) return;
    setBusy(true); setError(""); setSummary(null); setStored(0); setStage("Preparing a resumable import…");
    let job: TelegramImportStatus | null = null;
    let completed = new Set<number>();
    try {
      const fingerprint = await telegramFileFingerprint(file);
      const result = await streamTelegramExport(file, {
        onHeader: async (header) => {
          job = await api<TelegramImportStatus>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/imports`, {
            method: "POST", body: JSON.stringify({
              summary: { ...header, message_count: null, service_event_count: 0, participant_count: 0,
                media_count: 0, history_start: null, history_end: null, warnings: [] },
              source_id: telegramSource?.id, idempotency_key: fingerprint, bytes_total: file.size,
            }),
          });
          completed = new Set(job.completed_chunks || []);
          setStored(job.progress_current || 0); setWasResumed(Boolean(job.resumed && completed.size));
          setStage(completed.size ? "Resuming from the last completed batch…" : "Reading and securely importing messages…");
        },
        onBatch: async (messages, chunkIndex, processed) => {
          if (!job) throw new Error("The import could not be started.");
          if (completed.has(chunkIndex)) return;
          const activeJob = job as TelegramImportStatus;
          const next = await api<TelegramImportStatus>(API_URL, token,
            `/v2/workspaces/${detail.workspace.id}/telegram/imports/${activeJob.job_id}/chunks`, {
              method: "POST", body: JSON.stringify({ chunk_index: chunkIndex, messages, bytes_processed: processed }),
            });
          setStored(next.progress_current);
        },
        onProgress: (processed, _total, discovered) => { setBytesRead(processed); setMessagesRead(discovered); },
      });
      if (!job) throw new Error("The Telegram export did not contain an importable chat.");
      const activeJob = job as TelegramImportStatus;
      setStage("Finishing and verifying the import…");
      const finished = await api<TelegramImportStatus>(API_URL, token,
        `/v2/workspaces/${detail.workspace.id}/telegram/imports/${activeJob.job_id}/complete`, {
          method: "POST", body: JSON.stringify({ summary: result }),
        });
      setStored(finished.progress_current); setSummary(result); setStage("Import complete"); await refresh();
    } catch (e) {
      setStage("Import paused safely");
      setError(`${e instanceof Error ? e.message : "The import stopped."} Choose the same file and try again to resume.`);
    } finally { setBusy(false); }
  }

  const percentage = file?.size ? Math.min(100, Math.round(bytesRead / file.size * 100)) : 0;
  return <div className="mt-7 border-t border-white/10 pt-6">
    <Eyebrow>Telegram history</Eyebrow><h4 className="mt-2 text-lg font-semibold">Import the knowledge from before the bot joins</h4>
    <p className="mt-2 text-sm leading-6 text-slate-400">In Telegram Desktop, export the intended group as machine-readable JSON and choose its <code className="text-slate-300">result.json</code>. Comvoly reads it in small sections, so large exports do not have to fit in your laptop&apos;s memory. Media references are counted; the media files themselves are not uploaded yet.</p>
    <label className="mt-4 block cursor-pointer rounded-2xl border border-dashed border-white/20 bg-[#061124] p-5 text-center text-sm hover:border-[#ffcf4a]/60"><span className="font-semibold text-[#ffcf4a]">Choose Telegram result.json</span><input type="file" accept="application/json,.json" onChange={chooseFile} className="sr-only" /></label>
    {file && <div className="mt-4 rounded-2xl border border-white/10 bg-[#061124] p-4"><div className="flex flex-wrap justify-between gap-3"><div><p className="font-semibold">{file.name}</p><p className="mt-1 text-xs text-slate-500">{formatBytes(file.size)} · remains on this device while processed</p></div><button disabled={busy || Boolean(summary)} onClick={() => void importHistory()} className="rounded-xl bg-[#ffcf4a] px-5 py-2.5 text-sm font-bold text-[#07152b] disabled:opacity-60">{busy ? "Importing…" : error ? "Resume import" : summary ? "Import complete" : "Analyse and import"}</button></div>{stage && <div className="mt-4"><div className="flex justify-between gap-3 text-xs text-slate-400"><span>{stage}{wasResumed ? " (resumed)" : ""}</span><span>{percentage}%</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full bg-[#ffcf4a] transition-all" style={{ width: `${percentage}%` }} /></div><p className="mt-2 text-xs text-slate-500">Read {formatBytes(bytesRead)} · {messagesRead.toLocaleString()} found · {stored.toLocaleString()} stored</p></div>}</div>}
    {error && <p className="mt-3 rounded-xl bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
    {summary && <div className="mt-5 rounded-2xl border border-emerald-300/20 bg-emerald-300/[.04] p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold">{summary.community_name}</p><p className="mt-1 text-xs text-slate-500">{summary.export_type} · {summary.parser_version}</p></div><span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs text-emerald-200">Imported</span></div><div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Messages" value={summary.message_count} /><Metric label="People" value={summary.participant_count} /><Metric label="Media refs" value={summary.media_count} /><Metric label="Service events" value={summary.service_event_count} /></div><p className="mt-4 text-xs text-slate-500">{formatDate(summary.history_start)} – {formatDate(summary.history_end)}</p>{summary.warnings.map((warning) => <p key={warning} className="mt-2 text-xs text-amber-200">{warning}</p>)}</div>}
  </div>;
}

function WorkspaceIntelligencePanel({ detail, token }: { detail: WorkspaceDetail; token: string }) {
  const [question, setQuestion] = useState(""); const [answer, setAnswer] = useState<IntelligenceAnswer | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function submitQuestion() {
    if (busy || !question.trim()) return;
    setBusy(true); setError(""); setAnswer(null);
    try { setAnswer(await api<IntelligenceAnswer>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/intelligence/ask`, { method: "POST", body: JSON.stringify({ question }) })); }
    catch (e) { setError(e instanceof Error ? e.message : "Comvoly could not answer that question."); }
    finally { setBusy(false); }
  }
  return <div className="rounded-3xl border border-[#ffcf4a]/25 bg-[#ffcf4a]/[.035] p-6"><Eyebrow>Interpret community knowledge</Eyebrow><h3 className="mt-2 text-xl font-semibold">Ask {detail.workspace.name}</h3><p className="mt-2 text-sm leading-6 text-slate-400">Pilot answers use only this workspace and always show their supporting community messages.</p>
    <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={(event) => { event.preventDefault(); void submitQuestion(); }}><textarea required maxLength={1000} value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="What has this community said about…?" className="min-h-24 flex-1 rounded-2xl border border-white/15 bg-[#061124] p-4 text-sm" /><button disabled={busy || !question.trim()} aria-busy={busy} className="rounded-2xl bg-[#ffcf4a] px-6 py-3 font-bold text-[#07152b]">{busy ? "Interpreting…" : "Ask Comvoly"}</button></form>
    {error && <p className="mt-4 text-sm text-rose-200">{error}</p>}
    {answer && <div className="mt-5 border-t border-white/10 pt-5"><p className="leading-7 text-slate-100">{answer.answer}</p><p className="mt-2 text-xs text-slate-500">Checked against {answer.evidence_count} authorised messages · extractive pilot</p><div className="mt-4 space-y-3">{answer.citations.map((item) => <article key={item.content_id} className="rounded-xl bg-[#061124] p-4"><div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>{item.source_name} · {item.author}</span><span>{item.ingestion_method === "telegram_desktop_export" ? "Historical import" : item.ingestion_method === "telegram_bot_webhook" ? "Live Telegram" : "Community archive"} · Message {item.external_item_id}</span></div><p className="mt-2 text-sm leading-6 text-slate-300">{item.excerpt}</p></article>)}</div></div>}
  </div>;
}

function DeleteCommunity({ detail, token, onDeleted, setMessage }: { detail: WorkspaceDetail; token: string; onDeleted: () => Promise<void>; setMessage: (value: string) => void }) {
  const [busy, setBusy] = useState(false);
  async function remove() {
    const confirmation = window.prompt(`Delete ${detail.workspace.name}?\n\nType the community name exactly to confirm. Its connections and member access will stop immediately.`);
    if (confirmation === null) return;
    if (confirmation.trim() !== detail.workspace.name) { setMessage("Community name did not match. Nothing was deleted."); return; }
    setBusy(true); setMessage("");
    try {
      await api(API_URL, token, `/v2/workspaces/${detail.workspace.id}`, { method: "DELETE", body: JSON.stringify({ confirm_name: confirmation.trim() }) });
      await onDeleted(); setMessage(`${detail.workspace.name} was deleted. Its pilot data remains recoverable by an administrator.`);
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not delete this community."); }
    finally { setBusy(false); }
  }
  return <div className="rounded-3xl border border-rose-300/20 bg-rose-300/[.035] p-6"><h3 className="text-lg font-semibold">Delete community</h3><p className="mt-2 text-sm leading-6 text-slate-400">Removes this community from every member and stops all connected sources. During the pilot, underlying data is retained for recovery.</p><button disabled={busy} aria-busy={busy} onClick={() => void remove()} className="mt-5 rounded-xl border border-rose-300/35 px-4 py-2.5 text-sm font-semibold text-rose-200 hover:bg-rose-300/10">{busy ? "Deleting…" : "Delete community"}</button></div>;
}

function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-xl bg-white/[.04] p-3"><p className="text-lg font-semibold">{value.toLocaleString()}</p><p className="mt-1 text-xs text-slate-500">{label}</p></div>; }
function formatDate(value: string | null) { return value ? new Date(value).toLocaleDateString("en-GB") : "Unknown date"; }
function formatDateTime(value: string | null) { return value ? new Date(value).toLocaleString("en-GB") : "None yet"; }
function formatBytes(value: number) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(units.length - 1, Math.floor(Math.log(value) / Math.log(1024)));
  return `${(value / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
}

function Invite({ workspaceId, token, setMessage, refresh }: { workspaceId: string; token: string; setMessage: (value: string) => void; refresh: () => Promise<void> }) {
  const [role, setRole] = useState("member"); const [email, setEmail] = useState(""); const [link, setLink] = useState("");
  return <div className="rounded-3xl border border-white/10 bg-white/[.035] p-6"><h3 className="text-lg font-semibold">Invite a member</h3><p className="mt-2 text-sm text-slate-400">The link expires after 72 hours and works with an existing or new Comvoly account.</p><form className="mt-5 grid gap-3 sm:grid-cols-[1fr_10rem_auto]" onSubmit={async (event) => { event.preventDefault(); try { const result = await api<{ token: string }>(API_URL, token, `/v2/workspaces/${workspaceId}/invitations`, { method: "POST", body: JSON.stringify({ role, email_hint: email || null }) }); const inviteLink = `${window.location.origin}/account?invite=${encodeURIComponent(result.token)}`; setLink(inviteLink); await refresh(); } catch (e) { setMessage(e instanceof Error ? e.message : "Could not create invitation."); } }}><input type="email" placeholder="Email (optional reminder)" value={email} onChange={(e) => setEmail(e.target.value)} className="rounded-xl border border-white/15 bg-[#061124] px-3 py-2 text-sm" /><select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-xl border border-white/15 bg-[#061124] px-3 py-2 text-sm"><option value="member">Member</option><option value="moderator">Moderator</option><option value="administrator">Administrator</option></select><button className="rounded-xl bg-[#ffcf4a] px-4 py-2 text-sm font-bold text-[#07152b]">Create link</button></form>{link && <div className="mt-4 rounded-xl bg-[#061124] p-4"><p className="break-all text-xs text-slate-300">{link}</p><button onClick={async () => { await navigator.clipboard.writeText(link); setMessage("Invitation link copied."); }} className="mt-3 text-sm font-semibold text-[#ffcf4a]">Copy invitation link</button></div>}</div>;
}

function WorkspaceButton({ workspace, selected, onClick }: { workspace: WorkspaceSummary; selected: boolean; onClick: () => void }) { return <button onClick={onClick} className={`w-full rounded-2xl p-3 text-left ${selected ? "bg-white/10" : "hover:bg-white/[.05]"}`}><p className="font-medium">{workspace.name}</p><p className="mt-1 text-xs capitalize text-slate-500">{workspace.role}</p></button>; }
function EmptyState() { return <div className="rounded-3xl border border-white/10 bg-white/[.035] p-7"><h2 className="text-xl font-semibold">Your account is ready</h2><p className="mt-3 max-w-2xl leading-7 text-slate-400">Create a community workspace as an owner, or follow an invitation to join one. Registration alone never grants access to existing community knowledge.</p></div>; }
function Shell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) { return <main className="min-h-screen bg-[#07152d] px-4 py-8 text-white sm:px-8"><div className={`mx-auto ${wide ? "max-w-6xl" : "max-w-4xl"}`}><Link href="/" className="text-2xl font-black">COMVOLY<span className="text-[#ffcf4a]">.</span></Link><section className="mt-8 rounded-[2rem] border border-white/10 bg-[#091a36] p-5 shadow-2xl sm:p-9">{children}</section></div></main>; }
function Field({ label, value, setValue, type = "text", autoComplete }: { label: string; value: string; setValue: (value: string) => void; type?: string; autoComplete: string }) { return <label className="block text-sm text-slate-300">{label}<input required type={type} autoComplete={autoComplete} value={value} onChange={(e) => setValue(e.target.value)} className="mt-2 w-full rounded-xl border border-white/15 bg-[#061124] px-4 py-3 outline-none focus:border-[#ffcf4a]" /></label>; }
function Notice({ children }: { children: React.ReactNode }) { return <p className="mt-5 rounded-xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm text-amber-100">{children}</p>; }
function Primary({ children }: { children: React.ReactNode }) { return <button className="w-full rounded-xl bg-[#ffcf4a] px-5 py-3 font-bold text-[#07152b]">{children}</button>; }
function Eyebrow({ children }: { children: React.ReactNode }) { return <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#ffcf4a]">{children}</p>; }
